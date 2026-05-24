"""Testes de hash de senha (S02-T02)."""

from __future__ import annotations

from app.auth.security import hash_password, verify_password


def test_hash_e_diferente_para_mesma_senha_por_causa_do_salt() -> None:
    a = hash_password("minha_senha")
    b = hash_password("minha_senha")
    assert a != b
    assert a.startswith("$2") and b.startswith("$2")  # bcrypt


def test_verify_password_retorna_true_para_senha_certa() -> None:
    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed) is True


def test_verify_password_retorna_false_para_senha_errada() -> None:
    hashed = hash_password("hunter2")
    assert verify_password("hunter3", hashed) is False


def test_verify_password_de_hash_malformado_nao_estoura() -> None:
    assert verify_password("qualquer", "isso_nao_eh_um_hash") is False
    assert verify_password("qualquer", "") is False
