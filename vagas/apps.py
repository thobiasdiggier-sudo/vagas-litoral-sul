from django.apps import AppConfig


class VagasConfig(AppConfig):
    """App público do portal (e onde ficam todos os modelos)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "vagas"
    verbose_name = "Vagas Litoral Sul"
