"""
Ponto de entrada ASGI (não é usado pelo projeto, mas fica disponível
caso a equipe queira publicar com um servidor ASGI no futuro).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
