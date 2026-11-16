from django.apps import AppConfig


class PrefeiturasConfig(AppConfig):
    """Área logada dos operadores das prefeituras (não tem modelos próprios)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "prefeituras"
    verbose_name = "Área da prefeitura"
