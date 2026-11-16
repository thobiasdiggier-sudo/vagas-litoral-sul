# Migração inicial: cria as tabelas do sistema.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import vagas.models
import vagas.validadores

ESCOLARIDADE = [
    ("nao_exige", "Não exige"),
    ("fundamental", "Ensino fundamental"),
    ("medio", "Ensino médio"),
    ("tecnico", "Curso técnico"),
    ("superior", "Ensino superior"),
]

TIPO_CONTRATO = [
    ("clt", "CLT"),
    ("temporario", "Temporário"),
    ("estagio", "Estágio"),
    ("aprendiz", "Jovem aprendiz"),
    ("autonomo_pj", "Autônomo / PJ"),
    ("outro", "Outro"),
]


def campos_da_vaga(related_name):
    """Campos comuns (modelo abstrato DadosVaga) de Vaga e SolicitacaoVaga."""
    return [
        ("titulo", models.CharField(max_length=150, verbose_name="título da vaga")),
        ("descricao", models.TextField(verbose_name="descrição das atividades")),
        ("empresa", models.CharField(max_length=150, verbose_name="empresa / contratante")),
        (
            "tipo_contrato",
            models.CharField(choices=TIPO_CONTRATO, max_length=20, verbose_name="tipo de contrato"),
        ),
        (
            "escolaridade",
            models.CharField(choices=ESCOLARIDADE, max_length=20, verbose_name="escolaridade mínima"),
        ),
        ("quantidade", models.PositiveIntegerField(default=1, verbose_name="quantidade de vagas")),
        (
            "salario",
            models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Deixe em branco para exibir “A combinar”.",
                max_digits=10,
                null=True,
                verbose_name="salário (R$)",
            ),
        ),
        (
            "jornada",
            models.CharField(
                help_text="Ex.: 44 horas semanais, segunda a sábado",
                max_length=100,
                verbose_name="jornada de trabalho",
            ),
        ),
        ("requisitos", models.TextField(blank=True, verbose_name="requisitos")),
        ("beneficios", models.TextField(blank=True, verbose_name="benefícios")),
        (
            "pcd",
            models.BooleanField(default=False, verbose_name="vaga para pessoa com deficiência (PcD)"),
        ),
        (
            "forma_candidatura",
            models.TextField(
                help_text="Informe e-mail, telefone, endereço ou link para o candidato.",
                verbose_name="como se candidatar",
            ),
        ),
        (
            "area",
            models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name=related_name,
                to="vagas.areaatuacao",
                verbose_name="área de atuação",
            ),
        ),
        (
            "municipio",
            models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name=related_name,
                to="vagas.municipio",
                verbose_name="município",
            ),
        ),
    ]


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AreaAtuacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=80, unique=True, verbose_name="nome")),
            ],
            options={
                "verbose_name": "área de atuação",
                "verbose_name_plural": "áreas de atuação",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Municipio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=100, unique=True, verbose_name="nome")),
                (
                    "slug",
                    models.SlugField(
                        help_text="Parte do endereço da página do município. Ex.: tibau-do-sul",
                        max_length=120,
                        unique=True,
                        verbose_name="slug",
                    ),
                ),
                (
                    "ativo",
                    models.BooleanField(
                        default=True,
                        help_text="Desmarque para ocultar o município no portal.",
                        verbose_name="ativo",
                    ),
                ),
            ],
            options={
                "verbose_name": "município",
                "verbose_name_plural": "municípios",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Prefeitura",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "orgao_responsavel",
                    models.CharField(
                        help_text="Ex.: Secretaria Municipal do Trabalho e Assistência Social",
                        max_length=150,
                        verbose_name="órgão responsável",
                    ),
                ),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="e-mail de contato")),
                ("telefone", models.CharField(blank=True, max_length=20, verbose_name="telefone de contato")),
                (
                    "municipio",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="prefeitura",
                        to="vagas.municipio",
                        verbose_name="município",
                    ),
                ),
            ],
            options={
                "verbose_name": "prefeitura",
                "verbose_name_plural": "prefeituras",
                "ordering": ["municipio__nome"],
            },
        ),
        migrations.CreateModel(
            name="OperadorPrefeitura",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "prefeitura",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="operadores",
                        to="vagas.prefeitura",
                        verbose_name="prefeitura",
                    ),
                ),
                (
                    "usuario",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="operador",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="usuário",
                    ),
                ),
            ],
            options={
                "verbose_name": "operador da prefeitura",
                "verbose_name_plural": "operadores das prefeituras",
                "ordering": ["prefeitura__municipio__nome", "usuario__username"],
            },
        ),
        migrations.CreateModel(
            name="Vaga",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                *campos_da_vaga("vagas"),
                (
                    "data_publicacao",
                    models.DateTimeField(default=django.utils.timezone.now, verbose_name="data de publicação"),
                ),
                (
                    "data_expiracao",
                    models.DateField(
                        default=vagas.models.data_expiracao_padrao,
                        help_text="A vaga deixa de aparecer no portal depois desta data.",
                        verbose_name="data de expiração",
                    ),
                ),
                (
                    "situacao",
                    models.CharField(
                        choices=[("aberta", "Aberta"), ("encerrada", "Encerrada"), ("expirada", "Expirada")],
                        default="aberta",
                        max_length=20,
                        verbose_name="situação",
                    ),
                ),
                (
                    "origem",
                    models.CharField(
                        choices=[
                            ("prefeitura", "Cadastrada pela prefeitura"),
                            ("empresa", "Solicitação de empresa"),
                        ],
                        default="prefeitura",
                        max_length=20,
                        verbose_name="origem",
                    ),
                ),
                ("atualizado_em", models.DateTimeField(auto_now=True, verbose_name="atualizado em")),
                (
                    "cadastrado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="vagas_cadastradas",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="cadastrado por",
                    ),
                ),
            ],
            options={
                "verbose_name": "vaga",
                "verbose_name_plural": "vagas",
                "ordering": ["-data_publicacao", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SolicitacaoVaga",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                *campos_da_vaga("solicitacaovagas"),
                (
                    "cnpj",
                    models.CharField(
                        blank=True,
                        help_text="Opcional.",
                        max_length=18,
                        validators=[vagas.validadores.validar_cnpj],
                        verbose_name="CNPJ",
                    ),
                ),
                ("nome_responsavel", models.CharField(blank=True, max_length=120, verbose_name="nome do responsável")),
                ("email_responsavel", models.EmailField(blank=True, max_length=254, verbose_name="e-mail do responsável")),
                (
                    "telefone_responsavel",
                    models.CharField(blank=True, max_length=20, verbose_name="telefone do responsável"),
                ),
                (
                    "aceite_termo",
                    models.BooleanField(default=False, verbose_name="aceite do termo de uso e privacidade"),
                ),
                (
                    "codigo_acompanhamento",
                    models.CharField(
                        editable=False, max_length=13, unique=True, verbose_name="código de acompanhamento"
                    ),
                ),
                (
                    "situacao",
                    models.CharField(
                        choices=[("pendente", "Pendente"), ("aprovada", "Aprovada"), ("recusada", "Recusada")],
                        default="pendente",
                        max_length=20,
                        verbose_name="situação",
                    ),
                ),
                ("motivo_recusa", models.TextField(blank=True, verbose_name="motivo da recusa")),
                ("moderado_em", models.DateTimeField(blank=True, null=True, verbose_name="moderado em")),
                ("ip_hash", models.CharField(blank=True, editable=False, max_length=64, verbose_name="hash do IP")),
                ("criado_em", models.DateTimeField(auto_now_add=True, verbose_name="enviada em")),
                (
                    "dados_anonimizados_em",
                    models.DateTimeField(blank=True, null=True, verbose_name="dados de contato apagados em"),
                ),
                (
                    "moderado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="solicitacoes_moderadas",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="moderado por",
                    ),
                ),
                (
                    "vaga_gerada",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="solicitacao_origem",
                        to="vagas.vaga",
                        verbose_name="vaga gerada",
                    ),
                ),
            ],
            options={
                "verbose_name": "solicitação de vaga",
                "verbose_name_plural": "solicitações de vagas",
                "ordering": ["-criado_em", "-id"],
            },
        ),
    ]
