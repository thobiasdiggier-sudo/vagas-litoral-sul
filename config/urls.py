"""
Rotas principais do projeto.

- /admin/        -> Django Admin (equipe do IFRN)
- /prefeitura/   -> área logada dos operadores das prefeituras
- /              -> portal público de vagas
"""

from django.contrib import admin
from django.urls import include, path

# Textos do Django Admin em português
admin.site.site_header = "Vagas Litoral Sul - Administração"
admin.site.site_title = "Vagas Litoral Sul"
admin.site.index_title = "Painel do IFRN Campus Canguaretama"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("prefeitura/", include("prefeituras.urls")),
    path("", include("vagas.urls")),
]
