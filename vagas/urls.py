"""Rotas da área pública."""

from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "vagas"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("buscar/", views.lista, name="lista"),
    path("vaga/<int:pk>/", views.detalhe, name="detalhe"),
    path("municipio/<slug:slug>/", views.municipio, name="municipio"),
    path("divulgue/", views.divulgar, name="divulgar"),
    path("divulgue/enviada/", views.divulgar_enviada, name="divulgar_enviada"),
    path("acompanhar/", views.acompanhar, name="acompanhar"),
    path("sobre/", TemplateView.as_view(template_name="vagas/sobre.html"), name="sobre"),
    path(
        "termo-de-uso/",
        TemplateView.as_view(template_name="vagas/termo.html"),
        name="termo",
    ),
    path("widget/ultimas-vagas/", views.widget_ultimas_vagas, name="widget"),
]
