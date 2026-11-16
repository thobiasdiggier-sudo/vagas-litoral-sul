#!/usr/bin/env python
"""Utilitário de linha de comando do Django para tarefas administrativas."""

import os
import sys


def main():
    """Executa o comando informado (runserver, migrate, test etc.)."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as erro:
        raise ImportError(
            "Não foi possível importar o Django. Ele está instalado e o "
            "ambiente virtual está ativado?"
        ) from erro
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
