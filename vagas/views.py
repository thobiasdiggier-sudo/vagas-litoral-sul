"""Views da área pública (visitantes e empresas, sem login)."""

from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.clickjacking import xframe_options_exempt

from .forms import AcompanharForm, FiltroVagasForm, SolicitacaoVagaForm
from .models import Municipio, SolicitacaoVaga, Vaga
from .seguranca import gerar_hash_ip, limite_de_envios_atingido, obter_ip_cliente

VAGAS_POR_PAGINA = 10

# Chave da sessão onde guardamos o código da última solicitação enviada
CHAVE_SESSAO_CODIGO = "codigo_ultima_solicitacao"


def _vagas_publicas():
    """Vagas visíveis ao público, já com município e área carregados."""
    return Vaga.objects.publicadas().select_related("municipio", "area")


def _paginar(request, queryset):
    """Divide o resultado em páginas (?page=2, ?page=3...)."""
    return Paginator(queryset, VAGAS_POR_PAGINA).get_page(request.GET.get("page"))


def inicio(request):
    """Página inicial: busca, filtros, contadores e vagas mais recentes."""
    publicadas = Vaga.objects.publicadas()
    contexto = {
        "form": FiltroVagasForm(),
        # Soma das quantidades (um anúncio pode ter várias vagas)
        "total_vagas": publicadas.aggregate(total=Sum("quantidade"))["total"] or 0,
        "total_anuncios": publicadas.count(),
        "total_municipios": Municipio.objects.filter(ativo=True).count(),
        "ultimas_vagas": _vagas_publicas()[:6],
    }
    return render(request, "vagas/inicio.html", contexto)


def lista(request):
    """Lista paginada de vagas abertas, com busca e filtros."""
    form = FiltroVagasForm(request.GET or None)
    vagas = _vagas_publicas()
    if form.is_bound and form.is_valid():
        vagas = form.filtrar(vagas)

    contexto = {"form": form, "pagina": _paginar(request, vagas)}
    return render(request, "vagas/lista.html", contexto)


def detalhe(request, pk):
    """
    Detalhe da vaga. Se a vaga não estiver mais publicada, a página mostra
    um aviso (em vez de erro), pois o link pode ter sido compartilhado.
    """
    vaga = get_object_or_404(Vaga.objects.select_related("municipio", "area"), pk=pk)

    texto = (
        f"Vaga: {vaga.titulo} em {vaga.municipio.nome}/RN. "
        f"Veja como se candidatar: {request.build_absolute_uri()}"
    )
    contexto = {
        "vaga": vaga,
        "link_whatsapp": "https://wa.me/?text=" + quote(texto),
    }
    return render(request, "vagas/detalhe.html", contexto)


def municipio(request, slug):
    """Página com as vagas abertas de um município."""
    cidade = get_object_or_404(Municipio, slug=slug, ativo=True)
    vagas = _vagas_publicas().filter(municipio=cidade)
    prefeitura = getattr(cidade, "prefeitura", None)

    contexto = {
        "municipio": cidade,
        "prefeitura": prefeitura,
        "pagina": _paginar(request, vagas),
    }
    return render(request, "vagas/municipio.html", contexto)


def divulgar(request):
    """Formulário "Divulgue sua vaga" (empresas, sem login)."""
    if request.method == "POST":
        form = SolicitacaoVagaForm(request.POST)
        ip_hash = gerar_hash_ip(obter_ip_cliente(request))

        # Limite de envios por IP (status 429 = muitas requisições)
        if limite_de_envios_atingido(ip_hash):
            messages.error(
                request,
                "Recebemos muitos envios a partir da sua conexão. "
                "Aguarde uma hora e tente novamente.",
            )
            return render(request, "vagas/divulgar.html", {"form": form}, status=429)

        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.ip_hash = ip_hash
            solicitacao.save()

            # O código vai para a sessão (e não para a URL), para não
            # aparecer no histórico do navegador nem nos logs do servidor.
            request.session[CHAVE_SESSAO_CODIGO] = solicitacao.codigo_acompanhamento
            messages.success(request, "Solicitação enviada com sucesso!")
            return redirect("vagas:divulgar_enviada")

        messages.error(request, "Corrija os campos indicados e envie novamente.")
    else:
        form = SolicitacaoVagaForm()

    return render(request, "vagas/divulgar.html", {"form": form})


def divulgar_enviada(request):
    """Confirmação do envio, com o código de acompanhamento."""
    codigo = request.session.get(CHAVE_SESSAO_CODIGO)
    if not codigo:
        return redirect("vagas:divulgar")
    return render(request, "vagas/divulgar_enviada.html", {"codigo": codigo})


def acompanhar(request):
    """Consulta da situação da solicitação pelo código de acompanhamento."""
    form = AcompanharForm(request.GET or None)
    solicitacao = None
    pesquisou = False

    if form.is_bound and form.is_valid():
        pesquisou = True
        solicitacao = (
            SolicitacaoVaga.objects.select_related("municipio", "vaga_gerada")
            .filter(codigo_acompanhamento=form.cleaned_data["codigo"])
            .first()
        )

    contexto = {"form": form, "solicitacao": solicitacao, "pesquisou": pesquisou}
    return render(request, "vagas/acompanhar.html", contexto)


@xframe_options_exempt
def widget_ultimas_vagas(request):
    """
    HTML leve com as 5 últimas vagas, para exibir em <iframe> no site do
    campus. Só esta view libera o X-Frame-Options; quem pode incorporar é
    definido pela variável WIDGET_FRAME_ANCESTORS (CSP frame-ancestors).
    """
    resposta = render(request, "vagas/widget.html", {"vagas": _vagas_publicas()[:5]})
    resposta["Content-Security-Policy"] = (
        f"frame-ancestors {settings.WIDGET_FRAME_ANCESTORS}"
    )
    return resposta
