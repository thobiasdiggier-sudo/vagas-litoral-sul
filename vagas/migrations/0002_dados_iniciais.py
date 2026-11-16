# Migração de dados: cadastra os municípios iniciais e as áreas de atuação.
# O administrador pode incluir outros depois, pelo Django Admin.

from django.db import migrations
from django.utils.text import slugify

MUNICIPIOS_INICIAIS = [
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

AREAS_INICIAIS = [
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


def criar_dados_iniciais(apps, schema_editor):
    """Cria municípios e áreas, sem duplicar se já existirem."""
    # Em migrações usamos apps.get_model (versão "histórica" do modelo)
    Municipio = apps.get_model("vagas", "Municipio")
    AreaAtuacao = apps.get_model("vagas", "AreaAtuacao")

    for nome in MUNICIPIOS_INICIAIS:
        Municipio.objects.get_or_create(nome=nome, defaults={"slug": slugify(nome)})

    for nome in AREAS_INICIAIS:
        AreaAtuacao.objects.get_or_create(nome=nome)


class Migration(migrations.Migration):
    dependencies = [
        ("vagas", "0001_initial"),
    ]

    operations = [
        # Ao desfazer a migração, os dados são mantidos (noop)
        migrations.RunPython(criar_dados_iniciais, migrations.RunPython.noop),
    ]
