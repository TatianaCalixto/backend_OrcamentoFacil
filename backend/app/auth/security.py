"""Utilitarios de hash de senha (S02-T02).

Wrapper sobre passlib[bcrypt]. Encapsulado aqui para que mudar de
algoritmo no futuro afete apenas este modulo.
"""

from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except ValueError:
        # hash malformado: tratar como nao-bate, sem propagar excecao.
        return False
