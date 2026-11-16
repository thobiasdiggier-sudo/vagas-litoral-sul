"""Formulários da área da prefeitura."""

from django import forms
from django.utils import timezone

from vagas.forms import CAMPOS_FORMULARIO_VAGA, WIDGETS_VAGA
from vagas.models import Municipio, Vaga, data_expiracao_padrao


class VagaForm(forms.ModelForm):
    """
    Cadastro e edição de vagas pela prefeitura.

    O operador NÃO escolhe o município: o campo é removido e a view grava
    o município do próprio operador. Só a equipe do IFRN escolhe.
    """

    data_expiracao = forms.DateField(
        label="Data de expiração",
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        help_text="A vaga deixa de aparecer no portal depois desta data.",
    )

    class Meta:
        model = Vaga
        fields = CAMPOS_FORMULARIO_VAGA + ["data_expiracao"]
        widgets = WIDGETS_VAGA
        localized_fields = ["salario"]

    def __init__(self, *args, eh_admin=False, **kwargs):
        super().__init__(*args, **kwargs)

        if eh_admin:
            self.fields["municipio"].queryset = Municipio.objects.all()
        else:
            del self.fields["municipio"]

        # Em uma vaga nova, sugere a data padrão (hoje + 30 dias)
        if not self.instance.pk:
            self.fields["data_expiracao"].initial = data_expiracao_padrao()

        self.fields["salario"].help_text = (
            "Ex.: 1.518,00. Deixe em branco para exibir “A combinar”."
        )

    def clean_data_expiracao(self):
        """Não permite escolher uma data no passado (a não ser manter a atual)."""
        data = self.cleaned_data["data_expiracao"]
        data_atual = self.instance.data_expiracao if self.instance.pk else None
        if data < timezone.localdate() and data != data_atual:
            raise forms.ValidationError("A data de expiração não pode estar no passado.")
        return data


class RecusaForm(forms.Form):
    """Motivo obrigatório ao recusar uma solicitação de empresa."""

    motivo_recusa = forms.CharField(
        label="Motivo da recusa",
        min_length=10,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="A empresa verá este texto ao consultar o código de acompanhamento.",
    )
