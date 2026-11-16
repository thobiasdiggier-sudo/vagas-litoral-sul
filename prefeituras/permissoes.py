"""
Regras de acesso da área da prefeitura (isolamento por município).

Como funciona:
- Toda view da área usa @login_required e, logo abaixo, @acesso_prefeitura.
- @acesso_prefeitura descobre quem é o usuário e guarda no request:
    request.eh_admin            -> True para a equipe do IFRN (is_staff)
    request.municipio_operador  -> município do operador (None para admin)
- Toda consulta passa por filtrar_por_municipio(). Assim, ao buscar uma
  vaga de outro município, o get_object_or_404 não a encontra e devolve
  404 (o operador nem fica sabendo que ela existe).
"""

from functools import wraps

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied


def eh_administrador(usuario) -> bool:
    """Equipe do IFRN: usuários ativos com acesso ao Django Admin."""
    return usuario.is_authenticated and usuario.is_active and usuario.is_staff


def obter_operador(usuario):
    """Retorna o OperadorPrefeitura do usuário, ou None se não houver."""
    try:
        return usuario.operador
    except ObjectDoesNotExist:
        return None


def acesso_prefeitura(view):
    """
    Decorador: libera a view para operadores de prefeitura e para a equipe
    do IFRN. Use sempre ABAIXO de @login_required.
    """

    @wraps(view)
    def view_protegida(request, *args, **kwargs):
        if eh_administrador(request.user):
            request.eh_admin = True
            request.municipio_operador = None
        else:
            operador = obter_operador(request.user)
            if operador is None:
                raise PermissionDenied(
                    "Seu usuário não está vinculado a nenhuma prefeitura."
                )
            request.eh_admin = False
            request.municipio_operador = operador.prefeitura.municipio
        return view(request, *args, **kwargs)

    return view_protegida


def apenas_administrador(view):
    """Decorador: libera a view só para a equipe do IFRN."""

    @wraps(view)
    def view_protegida(request, *args, **kwargs):
        if not getattr(request, "eh_admin", False):
            raise PermissionDenied("Página exclusiva da equipe do IFRN.")
        return view(request, *args, **kwargs)

    return view_protegida


def filtrar_por_municipio(queryset, request):
    """Restringe o queryset ao município do operador (admin vê tudo)."""
    if request.eh_admin:
        return queryset
    return queryset.filter(municipio=request.municipio_operador)
