"""
Validação de CNPJ.

Aceita o CNPJ numérico tradicional (11.222.333/0001-81) e também o novo
CNPJ alfanumérico da Receita Federal (ex.: 12.ABC.345/01DE-35), em que os
12 primeiros caracteres podem ter letras e os 2 últimos (dígitos
verificadores) continuam numéricos.

O cálculo é o mesmo para os dois formatos: cada caractere vale o seu
código ASCII menos 48. Assim, '0' a '9' valem 0 a 9, 'A' vale 17,
'B' vale 18, e assim por diante.
"""

import re

from django.core.exceptions import ValidationError

# Pesos usados no cálculo do 1º e do 2º dígito verificador
PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
PESOS_DV2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def limpar_cnpj(valor: str) -> str:
    """Remove pontos, barras, traços e espaços e coloca em maiúsculas."""
    return re.sub(r"[^0-9A-Za-z]", "", valor or "").upper()


def _calcular_digito(base: str, pesos: list[int]) -> str:
    """Calcula um dígito verificador pelo módulo 11."""
    soma = sum((ord(caractere) - 48) * peso for caractere, peso in zip(base, pesos))
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def cnpj_valido(valor: str) -> bool:
    """Retorna True se o CNPJ (com ou sem máscara) for válido."""
    cnpj = limpar_cnpj(valor)

    # 12 caracteres alfanuméricos + 2 dígitos verificadores numéricos
    if not re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", cnpj):
        return False

    # Sequências repetidas (00000000000000, 11111111111111...) são inválidas
    if len(set(cnpj)) == 1:
        return False

    digito1 = _calcular_digito(cnpj[:12], PESOS_DV1)
    digito2 = _calcular_digito(cnpj[:12] + digito1, PESOS_DV2)
    return cnpj[12:] == digito1 + digito2


def formatar_cnpj(valor: str) -> str:
    """Aplica a máscara 00.000.000/0000-00 a um CNPJ válido."""
    c = limpar_cnpj(valor)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def validar_cnpj(valor: str) -> None:
    """Validador do Django: só valida se o CNPJ foi informado (é opcional)."""
    if valor and not cnpj_valido(valor):
        raise ValidationError(
            "CNPJ inválido. Confira os números digitados.",
            code="cnpj_invalido",
        )
