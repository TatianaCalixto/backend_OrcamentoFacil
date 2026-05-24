"""Smoke test: garante que a suite de testes esta operacional."""


def test_smoke_assert_true() -> None:
    assert True


def test_smoke_python_version_minima() -> None:
    import sys

    assert sys.version_info >= (3, 12)
