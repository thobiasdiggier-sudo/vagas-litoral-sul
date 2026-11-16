"""
Comando de manutenção diária (para o cron):

    python manage.py expirar_vagas

1. Marca como "expirada" toda vaga aberta cuja data de expiração já passou.
2. LGPD: apaga os dados de contato das solicitações recusadas há mais de
   180 dias (configurável em DIAS_PARA_ANONIMIZAR_RECUSADAS).

Observação: a listagem pública já esconde vagas vencidas pela data, então
o portal continua correto mesmo que este comando deixe de rodar.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from vagas.models import SolicitacaoVaga, Vaga


class Command(BaseCommand):
    help = (
        "Marca como expiradas as vagas vencidas e apaga os dados de contato "
        "de solicitações recusadas antigas (LGPD)."
    )

    def handle(self, *args, **options):
        # 1) Expira as vagas vencidas (uma única consulta UPDATE)
        total_expiradas = Vaga.objects.vencidas().update(
            situacao=Vaga.Situacao.EXPIRADA,
            atualizado_em=timezone.now(),
        )
        self.stdout.write(f"Vagas marcadas como expiradas: {total_expiradas}")

        # 2) Anonimiza solicitações recusadas antigas
        limite = timezone.now() - timedelta(days=settings.DIAS_PARA_ANONIMIZAR_RECUSADAS)
        antigas = SolicitacaoVaga.objects.filter(
            situacao=SolicitacaoVaga.Situacao.RECUSADA,
            moderado_em__lt=limite,
            dados_anonimizados_em__isnull=True,
        )
        total_anonimizadas = 0
        for solicitacao in antigas:
            solicitacao.anonimizar()
            total_anonimizadas += 1
        self.stdout.write(
            f"Solicitações recusadas com dados de contato apagados: {total_anonimizadas}"
        )

        self.stdout.write(self.style.SUCCESS("Manutenção concluída."))
