#!/usr/bin/env python3
"""Gate de CI: pip-audit com gating por severidade (S20-T02, Fase 3).

O `pip-audit` não distingue severidade — ele falha o build em QUALQUER
vulnerabilidade encontrada. O critério da S20-T02 pede falha apenas em
High/Critical e *warning* (sem falhar) em Medium. Este wrapper resolve isso:

1. Roda `pip-audit -r <requirements> -f json` e lê o resultado.
2. Para cada vulnerabilidade, descobre a severidade consultando a API pública
   do OSV (https://api.osv.dev). A maioria dos avisos Python tem um alias GHSA
   cujo registro OSV traz `database_specific.severity`
   (CRITICAL/HIGH/MODERATE/LOW).
3. Aplica a política:
   - CRITICAL / HIGH ............ FALHA (exit 1) -> CI vermelho.
   - MODERATE (Medium) / LOW .... WARNING (não falha).
   - severidade indeterminada ... FALHA (fail-closed): uma vuln sem severidade
     conhecida não passa silenciosamente por um gate de segurança. Triagem
     manual + allowlist via `pip-audit --ignore-vuln <ID>` se for aceitável.

Uso:
    python scripts/ci_pip_audit.py -r requirements.txt

Exit codes: 0 = limpo ou só warnings; 1 = ao menos uma vuln que falha;
2 = erro ao executar/parsear o pip-audit.

Remediação documentada no README (seção "Segurança de dependências").
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

OSV_API = "https://api.osv.dev/v1/vulns/"
FAIL_SEVERITIES = {"CRITICAL", "HIGH"}
WARN_SEVERITIES = {"MODERATE", "MEDIUM", "LOW"}
HTTP_TIMEOUT = 15

# Allowlist de vulnerabilidades aceitas conscientemente: ID -> justificativa.
# Regra: toda entrada precisa de justificativa escrita e deve ser revisada
# quando o upstream publicar uma fix version. As ignoradas continuam sendo
# impressas no relatorio do CI — o gate silencia a falha, nunca o registro.
ALLOWLIST: dict[str, str] = {
    "PYSEC-2026-1325": (
        "ecdsa: entra apenas como dependencia transitiva de python-jose. "
        "O OrcaFacil assina e valida JWT com HS256 (HMAC, ver "
        "app/core/config.py:jwt_algorithm), portanto o codigo ECDSA "
        "vulneravel nunca e exercitado. Sem fix version publicada pelo "
        "upstream. Revisar se o projeto passar a usar ES256/RS256."
    ),
}


def run_pip_audit(requirement: str, ignore_ids: list[str] | None = None) -> list[dict]:
    """Roda pip-audit em JSON e devolve a lista de dependências auditadas.

    pip-audit retorna exit code != 0 quando encontra vulnerabilidades — isso é
    esperado e não é erro; nós lemos o JSON do stdout de qualquer forma. Só
    tratamos como erro real quando não há JSON parseável no stdout.
    """
    cmd = [
        sys.executable, "-m", "pip_audit",
        "-r", requirement,
        "-f", "json",
    ]
    for vuln_id in ignore_ids or []:
        cmd += ["--ignore-vuln", vuln_id]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stdout.strip()
    if not out:
        sys.stderr.write(
            "ci_pip_audit: pip-audit não produziu JSON. stderr:\n"
            + (proc.stderr or "(vazio)") + "\n"
        )
        raise SystemExit(2)
    try:
        data = json.loads(out)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"ci_pip_audit: falha ao parsear JSON do pip-audit: {exc}\n")
        sys.stderr.write(out[:2000] + "\n")
        raise SystemExit(2)
    # Formato v2: {"dependencies": [...]} ; formato antigo: lista direta.
    if isinstance(data, dict):
        return data.get("dependencies", [])
    return data


def _osv_get(vuln_id: str) -> dict | None:
    req = urllib.request.Request(
        OSV_API + vuln_id,
        headers={"User-Agent": "orcafacil-ci-pip-audit"},
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return None


def _severity_from_record(record: dict) -> str | None:
    """Extrai severidade textual de um registro OSV (GHSA traz em
    database_specific.severity). Retorna em maiúsculas ou None."""
    sev = (record.get("database_specific") or {}).get("severity")
    if isinstance(sev, str) and sev.strip():
        return sev.strip().upper()
    return None


def resolve_severity(vuln_id: str, aliases: list[str]) -> str | None:
    """Tenta o ID e os aliases (prioriza GHSA, que costuma ter severidade)."""
    candidates = [vuln_id] + list(aliases)
    candidates.sort(key=lambda i: (not i.startswith("GHSA"), i))  # GHSA primeiro
    for cand in candidates:
        record = _osv_get(cand)
        if record:
            sev = _severity_from_record(record)
            if sev:
                return sev
    return None


def main() -> int:
    # Saída em ASCII + stdout UTF-8: não crashar em consoles cp1252 (Windows).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="pip-audit com gate por severidade (OSV).")
    parser.add_argument("-r", "--requirement", required=True, help="arquivo requirements.txt")
    parser.add_argument(
        "--ignore-vuln",
        action="append",
        default=[],
        metavar="ID",
        help="ID extra a ignorar, alem da ALLOWLIST do script (repetivel).",
    )
    args = parser.parse_args()

    ignored = {**ALLOWLIST, **{vid: "informado via --ignore-vuln" for vid in args.ignore_vuln}}
    deps = run_pip_audit(args.requirement, list(ignored))

    failures: list[tuple] = []
    warnings: list[tuple] = []
    total_vulns = 0

    for dep in deps:
        name = dep.get("name", "?")
        version = dep.get("version", "?")
        for vuln in dep.get("vulns", []) or []:
            total_vulns += 1
            vid = vuln.get("id", "?")
            aliases = vuln.get("aliases", []) or []
            fixes = ", ".join(vuln.get("fix_versions", []) or []) or "—"
            severity = resolve_severity(vid, aliases) or "UNKNOWN"
            row = (name, version, vid, severity, fixes)
            if severity in FAIL_SEVERITIES or severity == "UNKNOWN":
                failures.append(row)
            else:
                warnings.append(row)

    def _print(title: str, rows: list[tuple]) -> None:
        print(f"\n{title} ({len(rows)}):")
        for name, version, vid, severity, fixes in rows:
            print(f"  [{severity:8}] {name} {version} — {vid} (fix: {fixes})")

    print("=" * 72)
    print(f"pip-audit + gate de severidade (OSV) — {total_vulns} vulnerabilidade(s) bruta(s)")
    print("=" * 72)

    if ignored:
        print(f"\nIGNORADAS por allowlist ({len(ignored)}) — risco aceito e justificado:")
        for vid, motivo in ignored.items():
            print(f"  [IGNORADA] {vid}\n             {motivo}")

    if warnings:
        _print("WARNINGS (Medium/Low — não falham o CI)", warnings)
    if failures:
        _print("FALHAS (High/Critical/indeterminada — quebram o CI)", failures)

    if failures:
        print(
            "\n[FALHA] CI vermelho: "
            f"{len(failures)} vulnerabilidade(s) de severidade alta/crítica/indeterminada.\n"
            "Remediação: atualize a dependência para a fix version indicada, ou — se "
            "o risco for aceito e justificado — adicione `--ignore-vuln <ID>` ao "
            "pip-audit. Ver README (seção 'Segurança de dependências')."
        )
        return 1

    if warnings:
        print("\n[WARN] Apenas vulnerabilidades Medium/Low: CI passa, mas convém remediar.")
    else:
        print("\n[OK] Nenhuma vulnerabilidade conhecida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
