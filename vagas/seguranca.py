"""
Proteção anti-spam do formulário "Divulgue sua vaga".

Em vez de guardar o IP do visitante (dado pessoal), guardamos apenas um
"hash" (impressão digital) dele, calculado com a SECRET_KEY. Com o hash
dá para contar quantos envios vieram do mesmo IP, mas não dá para
descobrir qual era o IP.
"""

import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def obter_ip_cliente(request) -> str:
    """
    Retorna o IP de quem fez a requisição.

    Atrás do Nginx, o REMOTE_ADDR é sempre o IP do próprio Nginx. Por isso,
    quando CONFIAR_PROXY_REVERSO=True, usamos o cabeçalho X-Real-IP, que o
    Nginx preenche (e sobrescreve) com o IP verdadeiro do visitante.
    """
    if settings.CONFIAR_PROXY_REVERSO:
        ip = request.META.get("HTTP_X_REAL_IP", "").strip()
        if ip:
            return ip
    return request.META.get("REMOTE_ADDR", "")


def gerar_hash_ip(ip: str) -> str:
    """Calcula o HMAC-SHA256 do IP usando a SECRET_KEY como chave."""
    return hmac.new(
        settings.SECRET_KEY.encode(), ip.encode(), hashlib.sha256
    ).hexdigest()


def limite_de_envios_atingido(ip_hash: str) -> bool:
    """True se este IP já enviou o máximo de solicitações na última hora."""
    # Importação aqui dentro para evitar importação circular com models.py
    from .models import SolicitacaoVaga

    uma_hora_atras = timezone.now() - timedelta(hours=1)
    envios = SolicitacaoVaga.objects.filter(
        ip_hash=ip_hash, criado_em__gte=uma_hora_atras
    ).count()
    return envios >= settings.LIMITE_SOLICITACOES_POR_HORA
