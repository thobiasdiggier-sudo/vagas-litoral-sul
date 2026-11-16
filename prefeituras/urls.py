"""Rotas da área da prefeitura (todas exigem login)."""

from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path, reverse_lazy

from . import views
from .permissoes import acesso_prefeitura

app_name = "prefeituras"


def _area_restrita(view):
    """Aplica login obrigatório + checagem de prefeitura a uma view pronta."""
    return login_required(acesso_prefeitura(view))


urlpatterns = [
    # Entrar e sair
    path(
        "entrar/",
        auth_views.LoginView.as_view(
            template_name="prefeituras/entrar.html",
            redirect_authenticated_user=True,
        ),
        name="entrar",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="sair"),
    # Troca de senha (pelo sistema de senhas do Django)
    path(
        "senha/",
        _area_restrita(
            auth_views.PasswordChangeView.as_view(
                template_name="prefeituras/senha.html",
                success_url=reverse_lazy("prefeituras:senha_alterada"),
            )
        ),
        name="senha",
    ),
    path(
        "senha/alterada/",
        _area_restrita(
            auth_views.PasswordChangeDoneView.as_view(
                template_name="prefeituras/senha_alterada.html"
            )
        ),
        name="senha_alterada",
    ),
    # Painel
    path("", views.painel, name="painel"),
    # Vagas
    path("vagas/", views.vagas_lista, name="vagas_lista"),
    path("vagas/nova/", views.vaga_criar, name="vaga_criar"),
    path("vagas/<int:pk>/editar/", views.vaga_editar, name="vaga_editar"),
    path("vagas/<int:pk>/encerrar/", views.vaga_encerrar, name="vaga_encerrar"),
    path("vagas/<int:pk>/renovar/", views.vaga_renovar, name="vaga_renovar"),
    path("vagas/<int:pk>/excluir/", views.vaga_excluir, name="vaga_excluir"),
    # Solicitações das empresas
    path("solicitacoes/", views.solicitacoes_lista, name="solicitacoes_lista"),
    path("solicitacoes/<int:pk>/", views.solicitacao_detalhe, name="solicitacao_detalhe"),
    path(
        "solicitacoes/<int:pk>/aprovar/",
        views.solicitacao_aprovar,
        name="solicitacao_aprovar",
    ),
    path(
        "solicitacoes/<int:pk>/recusar/",
        views.solicitacao_recusar,
        name="solicitacao_recusar",
    ),
    # Estatísticas (equipe do IFRN)
    path("estatisticas/", views.estatisticas, name="estatisticas"),
]
