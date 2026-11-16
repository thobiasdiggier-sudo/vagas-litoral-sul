"""Configuração do Django Admin (usado pela equipe do IFRN)."""

from django.contrib import admin, messages

from .models import (
    AreaAtuacao,
    Municipio,
    OperadorPrefeitura,
    Prefeitura,
    SolicitacaoVaga,
    Vaga,
)


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ["nome", "slug", "ativo"]
    list_filter = ["ativo"]
    list_editable = ["ativo"]
    search_fields = ["nome"]
    prepopulated_fields = {"slug": ["nome"]}


@admin.register(Prefeitura)
class PrefeituraAdmin(admin.ModelAdmin):
    list_display = ["municipio", "orgao_responsavel", "email", "telefone"]
    search_fields = ["municipio__nome", "orgao_responsavel", "email"]
    autocomplete_fields = ["municipio"]


@admin.register(OperadorPrefeitura)
class OperadorPrefeituraAdmin(admin.ModelAdmin):
    """
    Para criar um operador:
    1. Crie o usuário em "Autenticação e autorização > Usuários"
       (sem marcar "Membro da equipe").
    2. Cadastre aqui o vínculo do usuário com a prefeitura.
    Para desativar, use a ação "Desativar operadores selecionados".
    """

    list_display = ["usuario", "nome_completo", "prefeitura", "usuario_ativo"]
    list_filter = ["prefeitura__municipio", "usuario__is_active"]
    search_fields = [
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
        "prefeitura__municipio__nome",
    ]
    autocomplete_fields = ["usuario", "prefeitura"]
    actions = ["desativar_operadores", "ativar_operadores"]

    @admin.display(description="nome")
    def nome_completo(self, obj):
        return obj.usuario.get_full_name() or "-"

    @admin.display(description="ativo", boolean=True)
    def usuario_ativo(self, obj):
        return obj.usuario.is_active

    @admin.action(description="Desativar operadores selecionados")
    def desativar_operadores(self, request, queryset):
        for operador in queryset.select_related("usuario"):
            operador.usuario.is_active = False
            operador.usuario.save(update_fields=["is_active"])
        self.message_user(request, "Operadores desativados.", messages.SUCCESS)

    @admin.action(description="Reativar operadores selecionados")
    def ativar_operadores(self, request, queryset):
        for operador in queryset.select_related("usuario"):
            operador.usuario.is_active = True
            operador.usuario.save(update_fields=["is_active"])
        self.message_user(request, "Operadores reativados.", messages.SUCCESS)


@admin.register(AreaAtuacao)
class AreaAtuacaoAdmin(admin.ModelAdmin):
    list_display = ["nome"]
    search_fields = ["nome"]


@admin.register(Vaga)
class VagaAdmin(admin.ModelAdmin):
    list_display = [
        "titulo",
        "municipio",
        "area",
        "empresa",
        "situacao",
        "pcd",
        "data_publicacao",
        "data_expiracao",
        "origem",
    ]
    list_filter = [
        "situacao",
        "origem",
        "pcd",
        "municipio",
        "area",
        "tipo_contrato",
        "escolaridade",
    ]
    search_fields = ["titulo", "empresa", "descricao"]
    date_hierarchy = "data_publicacao"
    readonly_fields = ["cadastrado_por", "atualizado_em"]
    list_select_related = ["municipio", "area"]
    actions = ["encerrar_vagas", "renovar_vagas"]

    def save_model(self, request, obj, form, change):
        # Registra quem cadastrou a vaga pelo Admin
        if not obj.cadastrado_por:
            obj.cadastrado_por = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Encerrar vagas selecionadas")
    def encerrar_vagas(self, request, queryset):
        for vaga in queryset:
            vaga.encerrar()
        self.message_user(request, "Vagas encerradas.", messages.SUCCESS)

    @admin.action(description="Renovar por mais 30 dias")
    def renovar_vagas(self, request, queryset):
        for vaga in queryset:
            vaga.renovar()
        self.message_user(request, "Vagas renovadas por mais 30 dias.", messages.SUCCESS)


@admin.register(SolicitacaoVaga)
class SolicitacaoVagaAdmin(admin.ModelAdmin):
    """
    Para recusar com motivo, use a tela de moderação em /prefeitura/solicitacoes/
    (a equipe do IFRN vê as solicitações de todos os municípios).
    """

    list_display = [
        "codigo_acompanhamento",
        "titulo",
        "empresa",
        "municipio",
        "situacao",
        "criado_em",
        "moderado_por",
    ]
    list_filter = ["situacao", "municipio", "area"]
    search_fields = ["codigo_acompanhamento", "titulo", "empresa", "cnpj", "nome_responsavel"]
    date_hierarchy = "criado_em"
    readonly_fields = [
        "codigo_acompanhamento",
        "moderado_por",
        "moderado_em",
        "vaga_gerada",
        "criado_em",
        "dados_anonimizados_em",
    ]
    list_select_related = ["municipio", "moderado_por"]
    actions = ["aprovar_solicitacoes"]

    @admin.action(description="Aprovar solicitações pendentes selecionadas")
    def aprovar_solicitacoes(self, request, queryset):
        aprovadas = 0
        for solicitacao in queryset.filter(situacao=SolicitacaoVaga.Situacao.PENDENTE):
            solicitacao.aprovar(request.user)
            aprovadas += 1
        self.message_user(
            request, f"{aprovadas} solicitação(ões) aprovada(s).", messages.SUCCESS
        )
