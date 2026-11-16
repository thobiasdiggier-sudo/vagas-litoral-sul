"""
Views da área da prefeitura.

TODAS as views usam @login_required + @acesso_prefeitura e buscam os
dados com filtrar_por_municipio(). Ver prefeituras/permissoes.py.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from vagas.models import AreaAtuacao, Municipio, SolicitacaoVaga, Vaga

from .forms import RecusaForm, VagaForm
from .permissoes import acesso_prefeitura, apenas_administrador, filtrar_por_municipio

ITENS_POR_PAGINA = 20


def _vagas_do_usuario(request):
    """Vagas que o usuário logado pode ver/alterar."""
    return filtrar_por_municipio(
        Vaga.objects.select_related("municipio", "area"), request
    )


def _solicitacoes_do_usuario(request):
    """Solicitações que o usuário logado pode ver/moderar."""
    return filtrar_por_municipio(
        SolicitacaoVaga.objects.select_related("municipio", "area"), request
    )


def _voltar(request):
    """
    Depois de uma ação rápida, volta para o painel ou para a lista.
    Só aceitamos esses dois destinos fixos (nunca uma URL vinda do
    formulário), para evitar redirecionamento para sites externos.
    """
    if request.POST.get("voltar_para") == "painel":
        return redirect("prefeituras:painel")
    return redirect("prefeituras:vagas_lista")


# ---------------------------------------------------------------------------
# Painel
# ---------------------------------------------------------------------------


@login_required
@acesso_prefeitura
def painel(request):
    """Resumo: vagas abertas, vagas que vencem em 7 dias e pendências."""
    hoje = timezone.localdate()
    vagas = _vagas_do_usuario(request)
    pendentes = _solicitacoes_do_usuario(request).filter(
        situacao=SolicitacaoVaga.Situacao.PENDENTE
    )

    contexto = {
        "total_abertas": vagas.publicadas().count(),
        "vagas_expirando": vagas.publicadas()
        .filter(data_expiracao__lte=hoje + timedelta(days=7))
        .order_by("data_expiracao"),
        "total_pendentes": pendentes.count(),
        "ultimas_pendentes": pendentes[:5],
    }
    return render(request, "prefeituras/painel.html", contexto)


# ---------------------------------------------------------------------------
# Vagas (CRUD)
# ---------------------------------------------------------------------------


@login_required
@acesso_prefeitura
def vagas_lista(request):
    """Lista das vagas do município, com busca e filtro por situação."""
    vagas = _vagas_do_usuario(request)

    termo = request.GET.get("q", "").strip()
    if termo:
        vagas = vagas.filter(Q(titulo__icontains=termo) | Q(empresa__icontains=termo))

    situacao = request.GET.get("situacao", "")
    if situacao in Vaga.Situacao.values:
        vagas = vagas.filter(situacao=situacao)

    pagina = Paginator(vagas, ITENS_POR_PAGINA).get_page(request.GET.get("page"))
    contexto = {
        "pagina": pagina,
        "termo": termo,
        "situacao": situacao,
        "situacoes": Vaga.Situacao.choices,
    }
    return render(request, "prefeituras/vagas_lista.html", contexto)


@login_required
@acesso_prefeitura
def vaga_criar(request):
    """Cadastro de nova vaga."""
    form = VagaForm(request.POST or None, eh_admin=request.eh_admin)

    if request.method == "POST" and form.is_valid():
        vaga = form.save(commit=False)
        if not request.eh_admin:
            # O operador sempre cadastra no próprio município
            vaga.municipio = request.municipio_operador
        vaga.origem = Vaga.Origem.PREFEITURA
        vaga.cadastrado_por = request.user
        vaga.save()
        messages.success(request, f"Vaga “{vaga.titulo}” cadastrada e publicada.")
        return redirect("prefeituras:vagas_lista")

    contexto = {"form": form, "titulo_pagina": "Nova vaga"}
    return render(request, "prefeituras/vaga_form.html", contexto)


@login_required
@acesso_prefeitura
def vaga_editar(request, pk):
    """Edição de uma vaga do município."""
    vaga = get_object_or_404(_vagas_do_usuario(request), pk=pk)
    form = VagaForm(request.POST or None, instance=vaga, eh_admin=request.eh_admin)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vaga atualizada.")
        return redirect("prefeituras:vagas_lista")

    contexto = {"form": form, "vaga": vaga, "titulo_pagina": "Editar vaga"}
    return render(request, "prefeituras/vaga_form.html", contexto)


@login_required
@acesso_prefeitura
@require_POST
def vaga_encerrar(request, pk):
    """Ação rápida: encerra a vaga (sai do portal)."""
    vaga = get_object_or_404(_vagas_do_usuario(request), pk=pk)
    vaga.encerrar()
    messages.success(request, f"Vaga “{vaga.titulo}” encerrada.")
    return _voltar(request)


@login_required
@acesso_prefeitura
@require_POST
def vaga_renovar(request, pk):
    """Ação rápida: reabre a vaga por mais 30 dias a partir de hoje."""
    vaga = get_object_or_404(_vagas_do_usuario(request), pk=pk)
    vaga.renovar()
    messages.success(
        request,
        f"Vaga “{vaga.titulo}” renovada até {vaga.data_expiracao:%d/%m/%Y}.",
    )
    return _voltar(request)


@login_required
@acesso_prefeitura
def vaga_excluir(request, pk):
    """Exclusão definitiva (com página de confirmação)."""
    vaga = get_object_or_404(_vagas_do_usuario(request), pk=pk)

    if request.method == "POST":
        titulo = vaga.titulo
        vaga.delete()
        messages.success(request, f"Vaga “{titulo}” excluída.")
        return redirect("prefeituras:vagas_lista")

    return render(request, "prefeituras/vaga_excluir.html", {"vaga": vaga})


# ---------------------------------------------------------------------------
# Moderação das solicitações das empresas
# ---------------------------------------------------------------------------


@login_required
@acesso_prefeitura
def solicitacoes_lista(request):
    """Fila de moderação (por padrão, mostra as pendentes)."""
    solicitacoes = _solicitacoes_do_usuario(request)

    situacao = request.GET.get("situacao", SolicitacaoVaga.Situacao.PENDENTE)
    if situacao in SolicitacaoVaga.Situacao.values:
        solicitacoes = solicitacoes.filter(situacao=situacao)
    else:
        situacao = "todas"

    # Pendentes: as mais antigas primeiro (fila); demais: as mais recentes
    if situacao == SolicitacaoVaga.Situacao.PENDENTE:
        solicitacoes = solicitacoes.order_by("criado_em", "id")

    pagina = Paginator(solicitacoes, ITENS_POR_PAGINA).get_page(request.GET.get("page"))
    contexto = {
        "pagina": pagina,
        "situacao": situacao,
        "situacoes": SolicitacaoVaga.Situacao.choices,
    }
    return render(request, "prefeituras/solicitacoes_lista.html", contexto)


@login_required
@acesso_prefeitura
def solicitacao_detalhe(request, pk):
    """Detalhe da solicitação, com os botões Aprovar e Recusar."""
    solicitacao = get_object_or_404(_solicitacoes_do_usuario(request), pk=pk)
    contexto = {"solicitacao": solicitacao, "form_recusa": RecusaForm()}
    return render(request, "prefeituras/solicitacao_detalhe.html", contexto)


@login_required
@acesso_prefeitura
@require_POST
def solicitacao_aprovar(request, pk):
    """Aprova a solicitação: ela vira uma vaga pública."""
    solicitacao = get_object_or_404(_solicitacoes_do_usuario(request), pk=pk)
    try:
        vaga = solicitacao.aprovar(request.user)
    except ValueError as erro:
        messages.error(request, str(erro))
        return redirect("prefeituras:solicitacao_detalhe", pk=pk)

    messages.success(request, f"Solicitação aprovada. A vaga “{vaga.titulo}” foi publicada.")
    return redirect("prefeituras:solicitacoes_lista")


@login_required
@acesso_prefeitura
@require_POST
def solicitacao_recusar(request, pk):
    """Recusa a solicitação, com motivo obrigatório."""
    solicitacao = get_object_or_404(_solicitacoes_do_usuario(request), pk=pk)
    form = RecusaForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Informe o motivo da recusa (mínimo de 10 caracteres).")
        contexto = {"solicitacao": solicitacao, "form_recusa": form}
        return render(request, "prefeituras/solicitacao_detalhe.html", contexto, status=400)

    try:
        solicitacao.recusar(request.user, form.cleaned_data["motivo_recusa"])
    except ValueError as erro:
        messages.error(request, str(erro))
        return redirect("prefeituras:solicitacao_detalhe", pk=pk)

    messages.success(request, "Solicitação recusada. A empresa verá o motivo informado.")
    return redirect("prefeituras:solicitacoes_lista")


# ---------------------------------------------------------------------------
# Estatísticas (somente equipe do IFRN)
# ---------------------------------------------------------------------------


@login_required
@acesso_prefeitura
@apenas_administrador
def estatisticas(request):
    """Vagas por município e por área; solicitações por situação."""
    hoje = timezone.localdate()
    filtro_abertas = Q(
        vagas__situacao=Vaga.Situacao.ABERTA, vagas__data_expiracao__gte=hoje
    )

    por_municipio = Municipio.objects.annotate(
        total=Count("vagas", distinct=True),
        abertas=Count("vagas", filter=filtro_abertas, distinct=True),
    ).order_by("-total", "nome")

    por_area = AreaAtuacao.objects.annotate(
        total=Count("vagas", distinct=True),
        abertas=Count("vagas", filter=filtro_abertas, distinct=True),
    ).order_by("-total", "nome")

    # Ex.: {"pendente": 3, "aprovada": 10, "recusada": 2}
    contagem = {
        linha["situacao"]: linha["total"]
        for linha in SolicitacaoVaga.objects.order_by()
        .values("situacao")
        .annotate(total=Count("id"))
    }
    solicitacoes = [
        (rotulo, contagem.get(valor, 0)) for valor, rotulo in SolicitacaoVaga.Situacao.choices
    ]

    # Maior valor, para desenhar as barras proporcionais no template
    maior_municipio = max([m.total for m in por_municipio] + [1])
    maior_area = max([a.total for a in por_area] + [1])

    contexto = {
        "por_municipio": por_municipio,
        "por_area": por_area,
        "solicitacoes": solicitacoes,
        "maior_municipio": maior_municipio,
        "maior_area": maior_area,
    }
    return render(request, "prefeituras/estatisticas.html", contexto)
