"""
Testes da área da prefeitura, com foco no ISOLAMENTO POR MUNICÍPIO:
um operador nunca vê nem altera dados de outro município.

Rode com:  python manage.py test
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from vagas.models import (
    AreaAtuacao,
    Escolaridade,
    Municipio,
    OperadorPrefeitura,
    Prefeitura,
    SolicitacaoVaga,
    TipoContrato,
    Vaga,
    data_expiracao_padrao,
)

SENHA = "SenhaDeTeste@123"


def criar_vaga(municipio, area, titulo, **extras):
    """Vaga mínima para os testes."""
    return Vaga.objects.create(
        titulo=titulo,
        descricao="Descrição",
        municipio=municipio,
        area=area,
        empresa="Empresa",
        tipo_contrato=TipoContrato.CLT,
        escolaridade=Escolaridade.MEDIO,
        jornada="44h",
        forma_candidatura="rh@empresa.com",
        **extras,
    )


def criar_solicitacao(municipio, area, titulo):
    """Solicitação pendente mínima para os testes."""
    return SolicitacaoVaga.objects.create(
        titulo=titulo,
        descricao="Descrição",
        municipio=municipio,
        area=area,
        empresa="Empresa da solicitação",
        tipo_contrato=TipoContrato.ESTAGIO,
        escolaridade=Escolaridade.TECNICO,
        quantidade=3,
        jornada="30h",
        pcd=True,
        forma_candidatura="estagio@empresa.com",
        nome_responsavel="Responsável",
        email_responsavel="resp@empresa.com",
        telefone_responsavel="(84) 99999-1111",
        aceite_termo=True,
    )


def criar_operador(username, municipio):
    """Cria usuário + prefeitura + vínculo de operador."""
    usuario = get_user_model().objects.create_user(username=username, password=SENHA)
    prefeitura, _ = Prefeitura.objects.get_or_create(
        municipio=municipio, defaults={"orgao_responsavel": "Secretaria do Trabalho"}
    )
    OperadorPrefeitura.objects.create(usuario=usuario, prefeitura=prefeitura)
    return usuario


def dados_vaga_formulario(area, **extras):
    """Dados do formulário de vaga da prefeitura."""
    dados = {
        "titulo": "Nova vaga da prefeitura",
        "area": area.pk,
        "empresa": "Comércio Local",
        "descricao": "Atividades.",
        "tipo_contrato": TipoContrato.CLT,
        "escolaridade": Escolaridade.FUNDAMENTAL,
        "quantidade": "1",
        "salario": "",
        "jornada": "44h",
        "requisitos": "",
        "beneficios": "",
        "forma_candidatura": "Comparecer à secretaria",
        "data_expiracao": data_expiracao_padrao().isoformat(),
    }
    dados.update(extras)
    return dados


class BaseAreaPrefeituraTest(TestCase):
    """Cenário: dois municípios, cada um com operador, vaga e solicitação."""

    @classmethod
    def setUpTestData(cls):
        cls.canguaretama = Municipio.objects.get(slug="canguaretama")
        cls.goianinha = Municipio.objects.get(slug="goianinha")
        cls.area = AreaAtuacao.objects.get(nome="Comércio")

        cls.operador_cang = criar_operador("op.cang", cls.canguaretama)
        cls.operador_goi = criar_operador("op.goi", cls.goianinha)

        cls.vaga_cang = criar_vaga(cls.canguaretama, cls.area, "Vaga de Canguaretama")
        cls.vaga_goi = criar_vaga(cls.goianinha, cls.area, "Vaga de Goianinha")

        cls.solic_cang = criar_solicitacao(cls.canguaretama, cls.area, "Pedido de Canguaretama")
        cls.solic_goi = criar_solicitacao(cls.goianinha, cls.area, "Pedido de Goianinha")

    def entrar_como_canguaretama(self):
        self.client.force_login(self.operador_cang)


class AcessoTests(BaseAreaPrefeituraTest):
    """Login obrigatório e vínculo com prefeitura."""

    def test_anonimo_e_redirecionado_para_login(self):
        resposta = self.client.get(reverse("prefeituras:painel"))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("prefeituras:entrar"), resposta.url)

    def test_usuario_sem_prefeitura_recebe_403(self):
        usuario = get_user_model().objects.create_user(username="sem.vinculo", password=SENHA)
        self.client.force_login(usuario)
        resposta = self.client.get(reverse("prefeituras:painel"))
        self.assertEqual(resposta.status_code, 403)

    def test_login_pela_tela(self):
        resposta = self.client.post(
            reverse("prefeituras:entrar"), {"username": "op.cang", "password": SENHA}
        )
        self.assertRedirects(resposta, reverse("prefeituras:painel"))

    def test_operador_desativado_nao_entra(self):
        self.operador_cang.is_active = False
        self.operador_cang.save()
        entrou = self.client.login(username="op.cang", password=SENHA)
        self.assertFalse(entrou)

    def test_painel_resume_somente_o_proprio_municipio(self):
        self.entrar_como_canguaretama()
        resposta = self.client.get(reverse("prefeituras:painel"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["total_abertas"], 1)
        self.assertEqual(resposta.context["total_pendentes"], 1)
        self.assertContains(resposta, "Pedido de Canguaretama")
        self.assertNotContains(resposta, "Pedido de Goianinha")

    def test_estatisticas_so_para_equipe_do_ifrn(self):
        self.entrar_como_canguaretama()
        resposta = self.client.get(reverse("prefeituras:estatisticas"))
        self.assertEqual(resposta.status_code, 403)

    def test_troca_de_senha(self):
        self.entrar_como_canguaretama()
        resposta = self.client.post(
            reverse("prefeituras:senha"),
            {
                "old_password": SENHA,
                "new_password1": "NovaSenhaForte@2026",
                "new_password2": "NovaSenhaForte@2026",
            },
        )
        self.assertRedirects(resposta, reverse("prefeituras:senha_alterada"))
        self.operador_cang.refresh_from_db()
        self.assertTrue(self.operador_cang.check_password("NovaSenhaForte@2026"))


class IsolamentoVagasTests(BaseAreaPrefeituraTest):
    """Operador NÃO acessa vagas de outro município."""

    def test_lista_mostra_so_vagas_do_municipio(self):
        self.entrar_como_canguaretama()
        resposta = self.client.get(reverse("prefeituras:vagas_lista"))
        self.assertContains(resposta, "Vaga de Canguaretama")
        self.assertNotContains(resposta, "Vaga de Goianinha")

    def test_nao_edita_vaga_de_outro_municipio(self):
        self.entrar_como_canguaretama()
        url = reverse("prefeituras:vaga_editar", args=[self.vaga_goi.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

        resposta = self.client.post(url, dados_vaga_formulario(self.area, titulo="Invadida"))
        self.assertEqual(resposta.status_code, 404)
        self.vaga_goi.refresh_from_db()
        self.assertEqual(self.vaga_goi.titulo, "Vaga de Goianinha")

    def test_nao_encerra_nem_renova_vaga_de_outro_municipio(self):
        self.entrar_como_canguaretama()
        for rota in ["prefeituras:vaga_encerrar", "prefeituras:vaga_renovar"]:
            resposta = self.client.post(reverse(rota, args=[self.vaga_goi.pk]))
            self.assertEqual(resposta.status_code, 404)
        self.vaga_goi.refresh_from_db()
        self.assertEqual(self.vaga_goi.situacao, Vaga.Situacao.ABERTA)

    def test_nao_exclui_vaga_de_outro_municipio(self):
        self.entrar_como_canguaretama()
        resposta = self.client.post(reverse("prefeituras:vaga_excluir", args=[self.vaga_goi.pk]))
        self.assertEqual(resposta.status_code, 404)
        self.assertTrue(Vaga.objects.filter(pk=self.vaga_goi.pk).exists())

    def test_nova_vaga_sempre_no_municipio_do_operador(self):
        self.entrar_como_canguaretama()
        # Mesmo enviando o município de outra cidade, o campo é ignorado
        dados = dados_vaga_formulario(self.area, municipio=self.goianinha.pk)
        resposta = self.client.post(reverse("prefeituras:vaga_criar"), dados)
        self.assertRedirects(resposta, reverse("prefeituras:vagas_lista"))

        vaga = Vaga.objects.get(titulo="Nova vaga da prefeitura")
        self.assertEqual(vaga.municipio, self.canguaretama)
        self.assertEqual(vaga.origem, Vaga.Origem.PREFEITURA)
        self.assertEqual(vaga.cadastrado_por, self.operador_cang)

    def test_encerrar_e_renovar_a_propria_vaga(self):
        self.entrar_como_canguaretama()
        self.client.post(reverse("prefeituras:vaga_encerrar", args=[self.vaga_cang.pk]))
        self.vaga_cang.refresh_from_db()
        self.assertEqual(self.vaga_cang.situacao, Vaga.Situacao.ENCERRADA)

        self.client.post(reverse("prefeituras:vaga_renovar", args=[self.vaga_cang.pk]))
        self.vaga_cang.refresh_from_db()
        self.assertEqual(self.vaga_cang.situacao, Vaga.Situacao.ABERTA)
        self.assertEqual(
            self.vaga_cang.data_expiracao, timezone.localdate() + timedelta(days=30)
        )

    def test_acoes_rapidas_exigem_post(self):
        self.entrar_como_canguaretama()
        resposta = self.client.get(reverse("prefeituras:vaga_encerrar", args=[self.vaga_cang.pk]))
        self.assertEqual(resposta.status_code, 405)


class IsolamentoSolicitacoesTests(BaseAreaPrefeituraTest):
    """Operador NÃO acessa solicitações de outro município."""

    def test_fila_mostra_so_o_proprio_municipio(self):
        self.entrar_como_canguaretama()
        resposta = self.client.get(reverse("prefeituras:solicitacoes_lista"))
        self.assertContains(resposta, "Pedido de Canguaretama")
        self.assertNotContains(resposta, "Pedido de Goianinha")

    def test_nao_ve_solicitacao_de_outro_municipio(self):
        self.entrar_como_canguaretama()
        url = reverse("prefeituras:solicitacao_detalhe", args=[self.solic_goi.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_nao_aprova_nem_recusa_solicitacao_de_outro_municipio(self):
        self.entrar_como_canguaretama()
        aprovar = reverse("prefeituras:solicitacao_aprovar", args=[self.solic_goi.pk])
        recusar = reverse("prefeituras:solicitacao_recusar", args=[self.solic_goi.pk])
        self.assertEqual(self.client.post(aprovar).status_code, 404)
        self.assertEqual(
            self.client.post(recusar, {"motivo_recusa": "Tentativa indevida"}).status_code, 404
        )
        self.solic_goi.refresh_from_db()
        self.assertEqual(self.solic_goi.situacao, SolicitacaoVaga.Situacao.PENDENTE)
        self.assertFalse(Vaga.objects.filter(titulo="Pedido de Goianinha").exists())


class ModeracaoTests(BaseAreaPrefeituraTest):
    """Aprovação gera vaga; recusa exige motivo."""

    def test_aprovacao_gera_vaga_publicada(self):
        self.entrar_como_canguaretama()
        resposta = self.client.post(
            reverse("prefeituras:solicitacao_aprovar", args=[self.solic_cang.pk])
        )
        self.assertRedirects(resposta, reverse("prefeituras:solicitacoes_lista"))

        self.solic_cang.refresh_from_db()
        self.assertEqual(self.solic_cang.situacao, SolicitacaoVaga.Situacao.APROVADA)
        self.assertEqual(self.solic_cang.moderado_por, self.operador_cang)
        self.assertIsNotNone(self.solic_cang.moderado_em)

        vaga = self.solic_cang.vaga_gerada
        self.assertIsNotNone(vaga)
        self.assertEqual(vaga.titulo, "Pedido de Canguaretama")
        self.assertEqual(vaga.municipio, self.canguaretama)
        self.assertEqual(vaga.quantidade, 3)
        self.assertTrue(vaga.pcd)
        self.assertEqual(vaga.origem, Vaga.Origem.EMPRESA)
        self.assertTrue(vaga.esta_publicada)

        # A vaga aparece no portal público
        publica = self.client.get(reverse("vagas:lista"))
        self.assertContains(publica, "Pedido de Canguaretama")

    def test_nao_aprova_duas_vezes(self):
        self.entrar_como_canguaretama()
        url = reverse("prefeituras:solicitacao_aprovar", args=[self.solic_cang.pk])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(Vaga.objects.filter(titulo="Pedido de Canguaretama").count(), 1)

    def test_recusa_com_motivo(self):
        self.entrar_como_canguaretama()
        self.client.post(
            reverse("prefeituras:solicitacao_recusar", args=[self.solic_cang.pk]),
            {"motivo_recusa": "Faltam informações sobre o salário."},
        )
        self.solic_cang.refresh_from_db()
        self.assertEqual(self.solic_cang.situacao, SolicitacaoVaga.Situacao.RECUSADA)
        self.assertEqual(self.solic_cang.motivo_recusa, "Faltam informações sobre o salário.")
        self.assertIsNone(self.solic_cang.vaga_gerada)

    def test_recusa_sem_motivo_nao_e_aceita(self):
        self.entrar_como_canguaretama()
        resposta = self.client.post(
            reverse("prefeituras:solicitacao_recusar", args=[self.solic_cang.pk]),
            {"motivo_recusa": ""},
        )
        self.assertEqual(resposta.status_code, 400)
        self.solic_cang.refresh_from_db()
        self.assertEqual(self.solic_cang.situacao, SolicitacaoVaga.Situacao.PENDENTE)


class AdministradorTests(BaseAreaPrefeituraTest):
    """A equipe do IFRN (is_staff) vê e modera todos os municípios."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = get_user_model().objects.create_user(
            username="equipe.ifrn", password=SENHA, is_staff=True
        )

    def test_admin_ve_todos_os_municipios(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse("prefeituras:vagas_lista"))
        self.assertContains(resposta, "Vaga de Canguaretama")
        self.assertContains(resposta, "Vaga de Goianinha")

    def test_admin_modera_qualquer_solicitacao(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("prefeituras:solicitacao_aprovar", args=[self.solic_goi.pk]))
        self.solic_goi.refresh_from_db()
        self.assertEqual(self.solic_goi.situacao, SolicitacaoVaga.Situacao.APROVADA)

    def test_admin_cria_vaga_escolhendo_municipio(self):
        self.client.force_login(self.admin)
        dados = dados_vaga_formulario(self.area, municipio=self.goianinha.pk)
        self.client.post(reverse("prefeituras:vaga_criar"), dados)
        vaga = Vaga.objects.get(titulo="Nova vaga da prefeitura")
        self.assertEqual(vaga.municipio, self.goianinha)

    def test_admin_ve_estatisticas(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse("prefeituras:estatisticas"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Vagas por município")
