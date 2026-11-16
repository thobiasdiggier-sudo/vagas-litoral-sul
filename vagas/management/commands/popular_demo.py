"""
Cria dados de demonstração (NÃO use em produção):

    python manage.py popular_demo

- municípios e áreas (caso ainda não existam);
- uma prefeitura e um operador de teste por município
  (usuário "operador.<municipio>", senha padrão "Demo@Vagas2026");
- cerca de 20 vagas fictícias e algumas solicitações pendentes.

Use --senha para escolher outra senha para os operadores.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from vagas.models import (
    AreaAtuacao,
    Escolaridade,
    Municipio,
    OperadorPrefeitura,
    Prefeitura,
    SolicitacaoVaga,
    TipoContrato,
    Vaga,
)

SENHA_PADRAO = "Demo@Vagas2026"

MUNICIPIOS = [
    "Arês",
    "Baía Formosa",
    "Canguaretama",
    "Espírito Santo",
    "Goianinha",
    "Montanhas",
    "Pedro Velho",
    "Senador Georgino Avelino",
    "Tibau do Sul",
    "Vila Flor",
]

AREAS = [
    "Administração",
    "Agropecuária",
    "Comércio",
    "Construção Civil",
    "Educação",
    "Indústria",
    "Saúde",
    "Serviços",
    "Tecnologia",
    "Turismo/Hotelaria",
    "Outros",
]

# (título, área, empresa, contrato, escolaridade, salário ou None)
VAGAS_FICTICIAS = [
    ("Vendedor(a) de loja", "Comércio", "Loja Exemplo Calçados", TipoContrato.CLT, Escolaridade.MEDIO, "1518.00"),
    ("Recepcionista de pousada", "Turismo/Hotelaria", "Pousada Fictícia do Mar", TipoContrato.CLT, Escolaridade.MEDIO, "1600.00"),
    ("Camareira", "Turismo/Hotelaria", "Hotel Demonstração", TipoContrato.TEMPORARIO, Escolaridade.FUNDAMENTAL, "1518.00"),
    ("Garçom / Garçonete", "Turismo/Hotelaria", "Restaurante Sabor Fictício", TipoContrato.TEMPORARIO, Escolaridade.NAO_EXIGE, None),
    ("Auxiliar de cozinha", "Serviços", "Restaurante Sabor Fictício", TipoContrato.CLT, Escolaridade.FUNDAMENTAL, "1518.00"),
    ("Pedreiro", "Construção Civil", "Construtora Modelo", TipoContrato.AUTONOMO_PJ, Escolaridade.NAO_EXIGE, None),
    ("Servente de obras", "Construção Civil", "Construtora Modelo", TipoContrato.CLT, Escolaridade.NAO_EXIGE, "1518.00"),
    ("Técnico(a) de enfermagem", "Saúde", "Clínica Saúde Exemplo", TipoContrato.CLT, Escolaridade.TECNICO, "2100.00"),
    ("Agente administrativo", "Administração", "Escritório Contábil Fictício", TipoContrato.CLT, Escolaridade.MEDIO, "1700.00"),
    ("Estagiário(a) de informática", "Tecnologia", "Provedor Internet Exemplo", TipoContrato.ESTAGIO, Escolaridade.TECNICO, "700.00"),
    ("Técnico(a) de suporte em TI", "Tecnologia", "Provedor Internet Exemplo", TipoContrato.CLT, Escolaridade.TECNICO, "2000.00"),
    ("Jovem aprendiz administrativo", "Administração", "Supermercado Exemplo", TipoContrato.APRENDIZ, Escolaridade.MEDIO, "759.00"),
    ("Operador(a) de caixa", "Comércio", "Supermercado Exemplo", TipoContrato.CLT, Escolaridade.MEDIO, "1518.00"),
    ("Repositor(a) de mercadorias", "Comércio", "Supermercado Exemplo", TipoContrato.CLT, Escolaridade.FUNDAMENTAL, "1518.00"),
    ("Trabalhador(a) rural", "Agropecuária", "Fazenda Demonstração", TipoContrato.TEMPORARIO, Escolaridade.NAO_EXIGE, None),
    ("Operador(a) de máquinas", "Indústria", "Indústria Modelo de Alimentos", TipoContrato.CLT, Escolaridade.MEDIO, "1900.00"),
    ("Auxiliar de produção", "Indústria", "Indústria Modelo de Alimentos", TipoContrato.CLT, Escolaridade.FUNDAMENTAL, "1518.00"),
    ("Professor(a) de reforço escolar", "Educação", "Centro Educacional Exemplo", TipoContrato.AUTONOMO_PJ, Escolaridade.SUPERIOR, None),
    ("Monitor(a) de transporte escolar", "Educação", "Transportes Fictícios", TipoContrato.TEMPORARIO, Escolaridade.MEDIO, "1518.00"),
    ("Motorista de entregas", "Serviços", "Distribuidora Exemplo", TipoContrato.CLT, Escolaridade.FUNDAMENTAL, "1800.00"),
]


class Command(BaseCommand):
    help = "Cria municípios, áreas, operadores de teste e vagas fictícias."

    def add_arguments(self, parser):
        parser.add_argument(
            "--senha",
            default=SENHA_PADRAO,
            help=f"Senha dos operadores de teste (padrão: {SENHA_PADRAO})",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Semente fixa: os dados gerados são sempre os mesmos
        sorteio = random.Random(2026)
        Usuario = get_user_model()

        # 1) Municípios e áreas (a migração já cria, mas garantimos aqui)
        for nome in MUNICIPIOS:
            Municipio.objects.get_or_create(nome=nome)
        for nome in AREAS:
            AreaAtuacao.objects.get_or_create(nome=nome)

        # 2) Prefeitura e operador de teste para cada município
        for cidade in Municipio.objects.all():
            prefeitura, _criada = Prefeitura.objects.get_or_create(
                municipio=cidade,
                defaults={
                    "orgao_responsavel": "Secretaria Municipal do Trabalho (demonstração)",
                    "email": f"trabalho@{cidade.slug}.exemplo.gov.br",
                    "telefone": "(84) 3000-0000",
                },
            )
            nome_usuario = "operador." + cidade.slug.replace("-", "")
            usuario, _criado = Usuario.objects.get_or_create(
                username=nome_usuario,
                defaults={"first_name": "Operador", "last_name": cidade.nome},
            )
            usuario.set_password(options["senha"])
            usuario.is_active = True
            usuario.save()
            OperadorPrefeitura.objects.update_or_create(
                usuario=usuario, defaults={"prefeitura": prefeitura}
            )
            self.stdout.write(f"Operador: {nome_usuario}")

        # 3) Vagas fictícias (só se ainda não houver vagas)
        if Vaga.objects.exists():
            self.stdout.write(
                self.style.WARNING("Já existem vagas no banco; nenhuma vaga nova foi criada.")
            )
        else:
            self._criar_vagas(sorteio)
            self._criar_solicitacoes(sorteio)

        self.stdout.write(
            self.style.SUCCESS(
                f"Dados de demonstração prontos. Senha dos operadores: {options['senha']}"
            )
        )

    def _criar_vagas(self, sorteio):
        """Cria as 20 vagas fictícias, espalhadas pelos municípios."""
        municipios = list(Municipio.objects.all())
        areas = {area.nome: area for area in AreaAtuacao.objects.all()}
        hoje = timezone.localdate()

        for indice, (titulo, area, empresa, contrato, escolaridade, salario) in enumerate(
            VAGAS_FICTICIAS
        ):
            cidade = municipios[indice % len(municipios)]
            # Algumas vagas vencem nos próximos dias (aparecem no painel)
            dias_para_vencer = sorteio.choice([3, 5, 6, 12, 20, 25, 28, 30])
            Vaga.objects.create(
                titulo=titulo,
                descricao=(
                    f"Vaga fictícia para demonstração do sistema. Atuar como "
                    f"{titulo.lower()} em {cidade.nome}, seguindo as orientações "
                    f"da equipe e as normas da empresa."
                ),
                municipio=cidade,
                area=areas[area],
                empresa=empresa,
                tipo_contrato=contrato,
                escolaridade=escolaridade,
                quantidade=sorteio.randint(1, 4),
                salario=Decimal(salario) if salario else None,
                jornada="44 horas semanais",
                requisitos="Disponibilidade de horário. Experiência será um diferencial.",
                beneficios="Vale-transporte e vale-alimentação.",
                pcd=(indice % 4 == 0),
                forma_candidatura=(
                    "Enviar currículo para rh@exemplo.com.br ou comparecer à "
                    "Secretaria do Trabalho do município, das 8h às 12h."
                ),
                data_publicacao=timezone.now() - timedelta(days=sorteio.randint(0, 10), hours=indice),
                data_expiracao=hoje + timedelta(days=dias_para_vencer),
                origem=Vaga.Origem.PREFEITURA,
            )
        self.stdout.write(f"Vagas fictícias criadas: {len(VAGAS_FICTICIAS)}")

    def _criar_solicitacoes(self, sorteio):
        """Cria 3 solicitações pendentes para testar a moderação."""
        canguaretama = Municipio.objects.get(slug="canguaretama")
        goianinha = Municipio.objects.get(slug="goianinha")
        comercio = AreaAtuacao.objects.get(nome="Comércio")
        turismo = AreaAtuacao.objects.get(nome="Turismo/Hotelaria")

        exemplos = [
            ("Atendente de farmácia", canguaretama, comercio),
            ("Balconista de padaria", canguaretama, comercio),
            ("Cozinheiro(a) de pousada", goianinha, turismo),
        ]
        for titulo, cidade, area in exemplos:
            SolicitacaoVaga.objects.create(
                titulo=titulo,
                descricao="Solicitação fictícia enviada por empresa para demonstração.",
                municipio=cidade,
                area=area,
                empresa="Empresa Fictícia LTDA",
                tipo_contrato=TipoContrato.CLT,
                escolaridade=Escolaridade.MEDIO,
                quantidade=sorteio.randint(1, 3),
                jornada="44 horas semanais",
                forma_candidatura="Enviar currículo para contato@empresaficticia.com.br",
                cnpj="11.222.333/0001-81",
                nome_responsavel="Responsável Fictício",
                email_responsavel="contato@empresaficticia.com.br",
                telefone_responsavel="(84) 99999-0000",
                aceite_termo=True,
            )
        self.stdout.write(f"Solicitações pendentes criadas: {len(exemplos)}")
