"""
Modelos do Vagas Litoral Sul.

Todos os modelos do sistema ficam neste app (inclusive Prefeitura e
OperadorPrefeitura), para evitar importação circular entre os apps
"vagas" e "prefeituras". O app "prefeituras" só contém as telas da área
logada.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .validadores import validar_cnpj

# Por quantos dias uma vaga fica publicada, por padrão
DIAS_VALIDADE_PADRAO = 30


def data_expiracao_padrao():
    """Data de expiração padrão: hoje + 30 dias (no fuso do projeto)."""
    return timezone.localdate() + timedelta(days=DIAS_VALIDADE_PADRAO)


# ---------------------------------------------------------------------------
# Opções (choices) usadas em vários lugares
# ---------------------------------------------------------------------------


class TipoContrato(models.TextChoices):
    CLT = "clt", "CLT"
    TEMPORARIO = "temporario", "Temporário"
    ESTAGIO = "estagio", "Estágio"
    APRENDIZ = "aprendiz", "Jovem aprendiz"
    AUTONOMO_PJ = "autonomo_pj", "Autônomo / PJ"
    OUTRO = "outro", "Outro"


class Escolaridade(models.TextChoices):
    NAO_EXIGE = "nao_exige", "Não exige"
    FUNDAMENTAL = "fundamental", "Ensino fundamental"
    MEDIO = "medio", "Ensino médio"
    TECNICO = "tecnico", "Curso técnico"
    SUPERIOR = "superior", "Ensino superior"


# ---------------------------------------------------------------------------
# Municípios, prefeituras e operadores
# ---------------------------------------------------------------------------


class Municipio(models.Model):
    """Município participante do portal."""

    nome = models.CharField("nome", max_length=100, unique=True)
    slug = models.SlugField(
        "slug",
        max_length=120,
        unique=True,
        help_text="Parte do endereço da página do município. Ex.: tibau-do-sul",
    )
    ativo = models.BooleanField(
        "ativo",
        default=True,
        help_text="Desmarque para ocultar o município no portal.",
    )

    class Meta:
        verbose_name = "município"
        verbose_name_plural = "municípios"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        # Gera o slug a partir do nome, se não foi informado
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("vagas:municipio", args=[self.slug])


class Prefeitura(models.Model):
    """Órgão da prefeitura responsável pelas vagas de um município."""

    municipio = models.OneToOneField(
        Municipio,
        on_delete=models.PROTECT,
        related_name="prefeitura",
        verbose_name="município",
    )
    orgao_responsavel = models.CharField(
        "órgão responsável",
        max_length=150,
        help_text="Ex.: Secretaria Municipal do Trabalho e Assistência Social",
    )
    email = models.EmailField("e-mail de contato", blank=True)
    telefone = models.CharField("telefone de contato", max_length=20, blank=True)

    class Meta:
        verbose_name = "prefeitura"
        verbose_name_plural = "prefeituras"
        ordering = ["municipio__nome"]

    def __str__(self):
        return f"Prefeitura de {self.municipio.nome}"


class OperadorPrefeitura(models.Model):
    """
    Perfil que liga um usuário do Django a uma prefeitura.

    Um operador só enxerga e altera dados do município da sua prefeitura.
    Para desativar um operador, desmarque "Ativo" no usuário (Django Admin).
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="operador",
        verbose_name="usuário",
    )
    prefeitura = models.ForeignKey(
        Prefeitura,
        on_delete=models.PROTECT,
        related_name="operadores",
        verbose_name="prefeitura",
    )

    class Meta:
        verbose_name = "operador da prefeitura"
        verbose_name_plural = "operadores das prefeituras"
        ordering = ["prefeitura__municipio__nome", "usuario__username"]

    def __str__(self):
        return f"{self.usuario.get_username()} ({self.prefeitura.municipio.nome})"

    @property
    def municipio(self):
        """Atalho para o município do operador."""
        return self.prefeitura.municipio


class AreaAtuacao(models.Model):
    """Área de atuação da vaga (Comércio, Saúde, Turismo...)."""

    nome = models.CharField("nome", max_length=80, unique=True)

    class Meta:
        verbose_name = "área de atuação"
        verbose_name_plural = "áreas de atuação"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


# ---------------------------------------------------------------------------
# Vagas e solicitações
# ---------------------------------------------------------------------------


class DadosVaga(models.Model):
    """
    Modelo ABSTRATO com os campos comuns a Vaga e SolicitacaoVaga.

    Ele não cria tabela no banco: só evita repetir os mesmos campos nos
    dois modelos. Ao aprovar uma solicitação, estes campos são copiados
    para a nova Vaga (ver CAMPOS_DA_VAGA).

    O related_name "%(class)ss" vira "vagas" em Vaga e
    "solicitacaovagas" em SolicitacaoVaga.
    """

    titulo = models.CharField("título da vaga", max_length=150)
    descricao = models.TextField("descrição das atividades")
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name="%(class)ss",
        verbose_name="município",
    )
    area = models.ForeignKey(
        AreaAtuacao,
        on_delete=models.PROTECT,
        related_name="%(class)ss",
        verbose_name="área de atuação",
    )
    empresa = models.CharField("empresa / contratante", max_length=150)
    tipo_contrato = models.CharField(
        "tipo de contrato", max_length=20, choices=TipoContrato.choices
    )
    escolaridade = models.CharField(
        "escolaridade mínima", max_length=20, choices=Escolaridade.choices
    )
    quantidade = models.PositiveIntegerField("quantidade de vagas", default=1)
    salario = models.DecimalField(
        "salário (R$)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Deixe em branco para exibir “A combinar”.",
    )
    jornada = models.CharField(
        "jornada de trabalho",
        max_length=100,
        help_text="Ex.: 44 horas semanais, segunda a sábado",
    )
    requisitos = models.TextField("requisitos", blank=True)
    beneficios = models.TextField("benefícios", blank=True)
    pcd = models.BooleanField(
        "vaga para pessoa com deficiência (PcD)",
        default=False,
    )
    forma_candidatura = models.TextField(
        "como se candidatar",
        help_text="Informe e-mail, telefone, endereço ou link para o candidato.",
    )

    class Meta:
        abstract = True


# Nomes dos campos copiados da solicitação para a vaga ao aprovar
CAMPOS_DA_VAGA = [
    "titulo",
    "descricao",
    "municipio",
    "area",
    "empresa",
    "tipo_contrato",
    "escolaridade",
    "quantidade",
    "salario",
    "jornada",
    "requisitos",
    "beneficios",
    "pcd",
    "forma_candidatura",
]


class VagaQuerySet(models.QuerySet):
    """Consultas prontas e reutilizáveis para vagas."""

    def publicadas(self):
        """
        Vagas visíveis ao público: abertas, dentro do prazo e de municípios
        ativos. O filtro por data garante que a vaga some no dia seguinte à
        expiração, mesmo que o comando expirar_vagas não tenha rodado.
        """
        return self.filter(
            situacao=Vaga.Situacao.ABERTA,
            data_expiracao__gte=timezone.localdate(),
            municipio__ativo=True,
        )

    def vencidas(self):
        """Vagas ainda marcadas como abertas, mas com prazo vencido."""
        return self.filter(
            situacao=Vaga.Situacao.ABERTA,
            data_expiracao__lt=timezone.localdate(),
        )


class Vaga(DadosVaga):
    """Vaga de emprego publicada no portal."""

    class Situacao(models.TextChoices):
        ABERTA = "aberta", "Aberta"
        ENCERRADA = "encerrada", "Encerrada"
        EXPIRADA = "expirada", "Expirada"

    class Origem(models.TextChoices):
        PREFEITURA = "prefeitura", "Cadastrada pela prefeitura"
        EMPRESA = "empresa", "Solicitação de empresa"

    data_publicacao = models.DateTimeField("data de publicação", default=timezone.now)
    data_expiracao = models.DateField(
        "data de expiração",
        default=data_expiracao_padrao,
        help_text="A vaga deixa de aparecer no portal depois desta data.",
    )
    situacao = models.CharField(
        "situação",
        max_length=20,
        choices=Situacao.choices,
        default=Situacao.ABERTA,
    )
    origem = models.CharField(
        "origem",
        max_length=20,
        choices=Origem.choices,
        default=Origem.PREFEITURA,
    )
    cadastrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vagas_cadastradas",
        verbose_name="cadastrado por",
    )
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    objects = VagaQuerySet.as_manager()

    class Meta:
        verbose_name = "vaga"
        verbose_name_plural = "vagas"
        ordering = ["-data_publicacao", "-id"]

    def __str__(self):
        return f"{self.titulo} - {self.municipio.nome}"

    def get_absolute_url(self):
        return reverse("vagas:detalhe", args=[self.pk])

    @property
    def esta_publicada(self):
        """True se a vaga aparece para o público neste momento."""
        return (
            self.situacao == self.Situacao.ABERTA
            and self.data_expiracao >= timezone.localdate()
            and self.municipio.ativo
        )

    @property
    def situacao_exibida(self):
        """
        Situação mostrada na área da prefeitura. Uma vaga "aberta" com prazo
        vencido aparece como expirada mesmo antes de o cron rodar.
        """
        if (
            self.situacao == self.Situacao.ABERTA
            and self.data_expiracao < timezone.localdate()
        ):
            return "Expirada"
        return self.get_situacao_display()

    def encerrar(self):
        """Encerra a vaga (por exemplo, quando já foi preenchida)."""
        self.situacao = self.Situacao.ENCERRADA
        self.save(update_fields=["situacao", "atualizado_em"])

    def renovar(self):
        """Reabre a vaga, válida por mais 30 dias a partir de hoje."""
        self.situacao = self.Situacao.ABERTA
        self.data_expiracao = data_expiracao_padrao()
        self.save(update_fields=["situacao", "data_expiracao", "atualizado_em"])


# Letras e números sem caracteres que se confundem (0/O, 1/I)
ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class SolicitacaoVaga(DadosVaga):
    """
    Pedido de divulgação de vaga enviado por uma empresa (sem login).
    Só vira uma Vaga pública depois de aprovado pela prefeitura ou pelo IFRN.
    """

    class Situacao(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        APROVADA = "aprovada", "Aprovada"
        RECUSADA = "recusada", "Recusada"

    # Dados da empresa e do responsável (dados pessoais mínimos - LGPD)
    cnpj = models.CharField(
        "CNPJ",
        max_length=18,
        blank=True,
        validators=[validar_cnpj],
        help_text="Opcional.",
    )
    nome_responsavel = models.CharField("nome do responsável", max_length=120, blank=True)
    email_responsavel = models.EmailField("e-mail do responsável", blank=True)
    telefone_responsavel = models.CharField(
        "telefone do responsável", max_length=20, blank=True
    )
    aceite_termo = models.BooleanField(
        "aceite do termo de uso e privacidade", default=False
    )

    # Controle da solicitação
    codigo_acompanhamento = models.CharField(
        "código de acompanhamento", max_length=13, unique=True, editable=False
    )
    situacao = models.CharField(
        "situação",
        max_length=20,
        choices=Situacao.choices,
        default=Situacao.PENDENTE,
    )
    motivo_recusa = models.TextField("motivo da recusa", blank=True)
    moderado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacoes_moderadas",
        verbose_name="moderado por",
    )
    moderado_em = models.DateTimeField("moderado em", null=True, blank=True)
    vaga_gerada = models.OneToOneField(
        Vaga,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacao_origem",
        verbose_name="vaga gerada",
    )

    # Hash do IP (não guardamos o IP em si) para limitar envios por hora
    ip_hash = models.CharField("hash do IP", max_length=64, blank=True, editable=False)
    criado_em = models.DateTimeField("enviada em", auto_now_add=True)
    dados_anonimizados_em = models.DateTimeField(
        "dados de contato apagados em", null=True, blank=True
    )

    class Meta:
        verbose_name = "solicitação de vaga"
        verbose_name_plural = "solicitações de vagas"
        ordering = ["-criado_em", "-id"]

    def __str__(self):
        return f"{self.codigo_acompanhamento} - {self.titulo}"

    def save(self, *args, **kwargs):
        # Gera o código de acompanhamento na primeira gravação
        if not self.codigo_acompanhamento:
            self.codigo_acompanhamento = gerar_codigo_acompanhamento()
        super().save(*args, **kwargs)

    @transaction.atomic
    def aprovar(self, usuario):
        """
        Aprova a solicitação e cria a Vaga pública correspondente.
        Tudo acontece numa transação: ou grava as duas coisas, ou nenhuma.
        """
        if self.situacao != self.Situacao.PENDENTE:
            raise ValueError("Somente solicitações pendentes podem ser aprovadas.")

        dados = {campo: getattr(self, campo) for campo in CAMPOS_DA_VAGA}
        vaga = Vaga.objects.create(
            **dados,
            origem=Vaga.Origem.EMPRESA,
            cadastrado_por=usuario,
        )

        self.situacao = self.Situacao.APROVADA
        self.moderado_por = usuario
        self.moderado_em = timezone.now()
        self.vaga_gerada = vaga
        self.save()
        return vaga

    def recusar(self, usuario, motivo):
        """Recusa a solicitação, registrando o motivo."""
        if self.situacao != self.Situacao.PENDENTE:
            raise ValueError("Somente solicitações pendentes podem ser recusadas.")

        self.situacao = self.Situacao.RECUSADA
        self.motivo_recusa = motivo
        self.moderado_por = usuario
        self.moderado_em = timezone.now()
        self.save()

    def anonimizar(self):
        """Apaga os dados de contato (LGPD). Os dados da vaga são mantidos."""
        self.cnpj = ""
        self.nome_responsavel = ""
        self.email_responsavel = ""
        self.telefone_responsavel = ""
        self.ip_hash = ""
        self.dados_anonimizados_em = timezone.now()
        self.save(
            update_fields=[
                "cnpj",
                "nome_responsavel",
                "email_responsavel",
                "telefone_responsavel",
                "ip_hash",
                "dados_anonimizados_em",
            ]
        )


def gerar_codigo_acompanhamento():
    """Gera um código único no formato VLS-XXXX-XXXX."""
    while True:
        letras = "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(8))
        codigo = f"VLS-{letras[:4]}-{letras[4:]}"
        if not SolicitacaoVaga.objects.filter(codigo_acompanhamento=codigo).exists():
            return codigo
