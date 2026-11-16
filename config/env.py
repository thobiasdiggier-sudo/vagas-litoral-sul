"""
Leitura simples de variáveis de ambiente.

Este módulo substitui bibliotecas como o python-decouple para manter o
projeto com uma única dependência (o Django). Ele faz duas coisas:

1. Lê o arquivo ``.env`` (se existir) e coloca os valores em ``os.environ``,
   sem sobrescrever variáveis que já foram definidas no sistema.
2. Oferece funções pequenas para converter os valores para texto,
   booleano, inteiro e lista.
"""

import os
from pathlib import Path


def carregar_env(caminho: Path) -> None:
    """Carrega as linhas ``CHAVE=valor`` do arquivo .env para os.environ."""
    if not caminho.exists():
        return

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()

        # Ignora linhas vazias, comentários e linhas sem "="
        if not linha or linha.startswith("#") or "=" not in linha:
            continue

        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip()

        # Remove aspas externas apenas se forem um par igual: "valor" ou 'valor'.
        # Assim um valor como 'self' https://site (com aspas internas) é preservado.
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]

        # setdefault: variáveis reais do sistema têm prioridade sobre o .env
        os.environ.setdefault(chave, valor)


def texto(nome: str, padrao: str = "") -> str:
    """Retorna a variável como texto (ou o valor padrão)."""
    return os.environ.get(nome, padrao)


def booleano(nome: str, padrao: bool = False) -> bool:
    """Converte valores como 1, true, sim, yes e on para True."""
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "sim", "yes", "on"}


def inteiro(nome: str, padrao: int) -> int:
    """Converte a variável para número inteiro."""
    valor = os.environ.get(nome)
    if valor is None or not valor.strip():
        return padrao
    return int(valor)


def lista(nome: str, padrao: str = "") -> list[str]:
    """Converte 'a,b,c' em ['a', 'b', 'c'], ignorando itens vazios."""
    valor = os.environ.get(nome, padrao)
    return [item.strip() for item in valor.split(",") if item.strip()]
