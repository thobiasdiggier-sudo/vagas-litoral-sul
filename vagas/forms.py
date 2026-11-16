"""Formulários da área pública."""

from django import forms
from django.db.models import Q

from .models import (
    AreaAtuacao,
    Escolaridade,
    Municipio,
    SolicitacaoVaga,
    TipoContrato,
)
from .validadores import cnpj_valido, formatar_cnpj

# Campos da vaga, na ordem em que aparecem nos formulários.
# Também são usados pelo formulário da prefeitura (prefeituras/forms.py).
CAMPOS_FORMULARIO_VAGA = [
    "titulo",
    "municipio",
    "area",
    "empresa",
    "descricao",
    "tipo_contrato",
    "escolaridade",
    "quantidade",
    "salario",
    "jornada",
    "requisitos",
    "beneficios",
    "pcd",
    "forma_candidatura",
]

# Caixas de texto com altura adequada para celular
WIDGETS_VAGA = {
    "descricao": forms.Textarea(attrs={"rows": 5}),
    "requisitos": forms.Textarea(attrs={"rows": 3}),
    "beneficios": forms.Textarea(attrs={"rows": 3}),
    "forma_candidatura": forms.Textarea(
        attrs={
            "rows": 3,
            "placeholder": "Ex.: Enviar currículo para rh@empresa.com.br ou "
            "comparecer à Rua Principal, 100, das 8h às 12h.",
        }
    ),
    "quantidade": forms.NumberInput(attrs={"min": 1}),
}


class FiltroVagasForm(forms.Form):
    """Busca e filtros da lista pública (enviados por GET)."""

    q = forms.CharField(
        label="Palavra-chave",
        required=False,
        max_length=100,
        widget=forms.TextInput(
            attrs={"type": "search", "placeholder": "Ex.: vendedor, cozinha, recepção"}
        ),
    )
    municipio = forms.ModelChoiceField(
        label="Município",
        queryset=Municipio.objects.filter(ativo=True),
        required=False,
        empty_label="Todos os municípios",
    )
    area = forms.ModelChoiceField(
        label="Área de atuação",
        queryset=AreaAtuacao.objects.all(),
        required=False,
        empty_label="Todas as áreas",
    )
    escolaridade = forms.ChoiceField(
        label="Escolaridade mínima",
        choices=[("", "Qualquer escolaridade"), *Escolaridade.choices],
        required=False,
    )
    tipo_contrato = forms.ChoiceField(
        label="Tipo de contrato",
        choices=[("", "Qualquer tipo"), *TipoContrato.choices],
        required=False,
    )
    pcd = forms.BooleanField(label="Somente vagas PcD", required=False)

    def filtrar(self, vagas):
        """Aplica os filtros preenchidos ao queryset de vagas."""
        dados = self.cleaned_data

        if dados.get("q"):
            termo = dados["q"]
            vagas = vagas.filter(
                Q(titulo__icontains=termo)
                | Q(descricao__icontains=termo)
                | Q(empresa__icontains=termo)
                | Q(requisitos__icontains=termo)
            )
        if dados.get("municipio"):
            vagas = vagas.filter(municipio=dados["municipio"])
        if dados.get("area"):
            vagas = vagas.filter(area=dados["area"])
        if dados.get("escolaridade"):
            vagas = vagas.filter(escolaridade=dados["escolaridade"])
        if dados.get("tipo_contrato"):
            vagas = vagas.filter(tipo_contrato=dados["tipo_contrato"])
        if dados.get("pcd"):
            vagas = vagas.filter(pcd=True)
        return vagas


class SolicitacaoVagaForm(forms.ModelForm):
    """Formulário público "Divulgue sua vaga", preenchido pelas empresas."""

    # Campo "armadilha" (honeypot): fica escondido para pessoas, mas robôs
    # costumam preenchê-lo. Se vier preenchido, o envio é bloqueado.
    url_site = forms.CharField(
        label="Não preencha este campo",
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )

    class Meta:
        model = SolicitacaoVaga
        fields = CAMPOS_FORMULARIO_VAGA + [
            "cnpj",
            "nome_responsavel",
            "email_responsavel",
            "telefone_responsavel",
            "aceite_termo",
        ]
        widgets = {
            **WIDGETS_VAGA,
            "telefone_responsavel": forms.TextInput(
                attrs={"type": "tel", "autocomplete": "tel", "placeholder": "(84) 99999-9999"}
            ),
            "email_responsavel": forms.EmailInput(attrs={"autocomplete": "email"}),
            "nome_responsavel": forms.TextInput(attrs={"autocomplete": "name"}),
            "cnpj": forms.TextInput(attrs={"placeholder": "00.000.000/0000-00"}),
        }
        labels = {
            "aceite_termo": "Li e aceito o Termo de uso e privacidade",
        }
        # Aceita salário no formato brasileiro: 1.518,00
        localized_fields = ["salario"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Só municípios ativos aparecem na lista
        self.fields["municipio"].queryset = Municipio.objects.filter(ativo=True)
        self.fields["municipio"].empty_label = "Selecione o município"
        self.fields["area"].empty_label = "Selecione a área"

        # No modelo esses campos são opcionais (para poderem ser apagados
        # depois, conforme a LGPD), mas no envio eles são obrigatórios.
        for campo in ["nome_responsavel", "email_responsavel", "telefone_responsavel"]:
            self.fields[campo].required = True

        self.fields["salario"].help_text = (
            "Ex.: 1.518,00. Deixe em branco para exibir “A combinar”."
        )

    def clean_url_site(self):
        """Bloqueia o envio se o campo armadilha foi preenchido."""
        if self.cleaned_data.get("url_site"):
            raise forms.ValidationError("Envio bloqueado pela proteção anti-spam.")
        return ""

    def clean_cnpj(self):
        """Valida (numérico ou alfanumérico) e devolve o CNPJ com máscara."""
        cnpj = self.cleaned_data.get("cnpj", "").strip()
        if not cnpj:
            return ""
        if not cnpj_valido(cnpj):
            raise forms.ValidationError("CNPJ inválido. Confira os números digitados.")
        return formatar_cnpj(cnpj)

    def clean_aceite_termo(self):
        """O aceite do termo de uso é obrigatório (LGPD)."""
        aceite = self.cleaned_data.get("aceite_termo")
        if not aceite:
            raise forms.ValidationError(
                "Para enviar, é preciso aceitar o Termo de uso e privacidade."
            )
        return aceite


class AcompanharForm(forms.Form):
    """Consulta da situação de uma solicitação pelo código."""

    codigo = forms.CharField(
        label="Código de acompanhamento",
        max_length=20,
        widget=forms.TextInput(
            attrs={"placeholder": "VLS-XXXX-XXXX", "autocapitalize": "characters"}
        ),
    )

    def clean_codigo(self):
        """Ignora espaços e diferença entre maiúsculas e minúsculas."""
        return self.cleaned_data["codigo"].strip().upper()
