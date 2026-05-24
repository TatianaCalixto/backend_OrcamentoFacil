"""Smoke test: garante que a suite de testes esta operacional."""


def test_smoke_assert_true() -> None:
    assert False, "intencional: validacao CI vermelha (S00-T05)"


def test_smoke_python_version_minima() -> None:
    import sys

    assert sys.version_info >= (3, 12)
