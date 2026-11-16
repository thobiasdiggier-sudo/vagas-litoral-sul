"""
Testes da área pública, dos modelos e dos comandos.

Rode com:  python manage.py test
"""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    AreaAtuacao,
    Escolaridade,
    Municipio,
    SolicitacaoVaga,
    TipoContrato,
    Vaga,
)
from .validadores import cnpj_valido


def criar_vaga(municipio, area, **extras):
    """Cria uma vaga com valores padrão (pode sobrescrever qualquer campo)."""
    dados = {
        "titulo": "Auxiliar de vendas",
        "descricao": "Atendimento ao cliente.",
        "municipio": municipio,
        "area": area,
        "empresa": "Empresa Teste",
        "tipo_contrato": TipoContrato.CLT,
        "escolaridade": Escolaridade.MEDIO,
        "jornada": "44 horas semanais",
        "forma_candidatura": "rh@empresateste.com.br",
    }
    dados.update(extras)
    return Vaga.objects.create(**dados)


def dados_formulario_empresa(municipio, area, **extras):
    """Dados válidos do formulário "Divulgue sua vaga"."""
    dados = {
        "titulo": "Recepcionista",
        "municipio": municipio.pk,
        "area": area.pk,
        "empresa": "Pousada Teste",
        "descricao": "Atendimento na recepção.",
        "tipo_contrato": TipoContrato.CLT,
        "escolaridade": Escolaridade.MEDIO,
        "quantidade": "2",
        "salario": "1.600,00",
        "jornada": "44 horas semanais",
        "requisitos": "",
        "beneficios": "",
        "forma_candidatura": "Enviar currículo para rh@pousadateste.com.br",
        "cnpj": "",
        "nome_responsavel": "Maria Teste",
        "email_responsavel": "maria@pousadateste.com.br",
        "telefone_responsavel": "(84) 99999-0000",
        "aceite_termo": "on",
        "url_site": "",
    }
    dados.update(extras)
    return dados


class DadosIniciaisTests(TestCase):
    """A migração de dados cria os municípios e as áreas."""

    def test_municipios_iniciais(self):
        self.assertEqual(Municipio.objects.count(), 10)
        self.assertTrue(Municipio.objects.filter(slug="senador-georgino-avelino").exists())
        self.assertTrue(Municipio.objects.filter(slug="ares", nome="Arês").exists())

    def test_areas_iniciais(self):
        self.assertTrue(AreaAtuacao.objects.filter(nome="Turismo/Hotelaria").exists())
        self.assertEqual(AreaAtuacao.objects.count(), 11)


class ListagemPublicaTests(TestCase):
    """A lista pública mostra só vagas abertas e dentro do prazo."""

    @classmethod
    def setUpTestData(cls):
        cls.municipio = Municipio.objects.get(slug="canguaretama")
        cls.area = AreaAtuacao.objects.get(nome="Comércio")
        hoje = timezone.localdate()

        cls.aberta = criar_vaga(cls.municipio, cls.area, titulo="Vaga aberta")
        cls.vence_hoje = criar_vaga(
            cls.municipio, cls.area, titulo="Vaga vence hoje", data_expiracao=hoje
        )
        cls.encerrada = criar_vaga(
            cls.municipio, cls.area, titulo="Vaga encerrada", situacao=Vaga.Situacao.ENCERRADA
        )
        cls.expirada = criar_vaga(
            cls.municipio, cls.area, titulo="Vaga expirada", situacao=Vaga.Situacao.EXPIRADA
        )
        # Ainda "aberta" no banco, mas com prazo vencido (cron não rodou)
        cls.vencida = criar_vaga(
            cls.municipio,
            cls.area,
            titulo="Vaga vencida sem cron",
            data_expiracao=hoje - timedelta(days=1),
        )

    def test_lista_mostra_apenas_vagas_abertas_e_no_prazo(self):
        resposta = self.client.get(reverse("vagas:lista"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Vaga aberta")
        self.assertContains(resposta, "Vaga vence hoje")
        self.assertNotContains(resposta, "Vaga encerrada")
        self.assertNotContains(resposta, "Vaga expirada")
        self.assertNotContains(resposta, "Vaga vencida sem cron")

    def test_queryset_publicadas(self):
        publicadas = set(Vaga.objects.publicadas())
        self.assertEqual(publicadas, {self.aberta, self.vence_hoje})

    def test_municipio_inativo_nao_aparece(self):
        self.municipio.ativo = False
        self.municipio.save()
        resposta = self.client.get(reverse("vagas:lista"))
        self.assertNotContains(resposta, "Vaga aberta")

    def test_inicio_mostra_contadores(self):
        resposta = self.client.get(reverse("vagas:inicio"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["total_anuncios"], 2)
        self.assertEqual(resposta.context["total_municipios"], 10)

    def test_filtro_por_palavra_chave_e_pcd(self):
        criar_vaga(self.municipio, self.area, titulo="Cozinheiro PcD", pcd=True)
        resposta = self.client.get(reverse("vagas:lista"), {"q": "cozinheiro", "pcd": "on"})
        self.assertContains(resposta, "Cozinheiro PcD")
        self.assertNotContains(resposta, "Vaga aberta")

    def test_pagina_do_municipio(self):
        resposta = self.client.get(reverse("vagas:municipio", args=["canguaretama"]))
        self.assertContains(resposta, "Vaga aberta")
        self.assertNotContains(resposta, "Vaga encerrada")

    def test_detalhe_com_whatsapp(self):
        resposta = self.client.get(reverse("vagas:detalhe", args=[self.aberta.pk]))
        self.assertContains(resposta, "https://wa.me/?text=")
        self.assertContains(resposta, "Como se candidatar")

    def test_detalhe_de_vaga_encerrada_mostra_aviso(self):
        resposta = self.client.get(reverse("vagas:detalhe", args=[self.encerrada.pk]))
        self.assertContains(resposta, "não está mais disponível")
        self.assertNotContains(resposta, "rh@empresateste.com.br")


class WidgetTests(TestCase):
    """O widget pode ser exibido em iframe; o resto do site não."""

    @override_settings(WIDGET_FRAME_ANCESTORS="'self' https://portal.ifrn.edu.br")
    def test_widget_libera_iframe_com_csp(self):
        resposta = self.client.get(reverse("vagas:widget"))
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("X-Frame-Options", resposta.headers)
        self.assertEqual(
            resposta.headers["Content-Security-Policy"],
            "frame-ancestors 'self' https://portal.ifrn.edu.br",
        )

    def test_demais_paginas_bloqueiam_iframe(self):
        resposta = self.client.get(reverse("vagas:inicio"))
        self.assertEqual(resposta.headers["X-Frame-Options"], "DENY")

    def test_widget_mostra_no_maximo_5_vagas(self):
        municipio = Municipio.objects.get(slug="goianinha")
        area = AreaAtuacao.objects.get(nome="Serviços")
        for numero in range(7):
            criar_vaga(municipio, area, titulo=f"Vaga widget {numero}")
        resposta = self.client.get(reverse("vagas:widget"))
        self.assertEqual(len(resposta.context["vagas"]), 5)


class SolicitacaoEmpresaTests(TestCase):
    """Formulário "Divulgue sua vaga"."""

    @classmethod
    def setUpTestData(cls):
        cls.municipio = Municipio.objects.get(slug="tibau-do-sul")
        cls.area = AreaAtuacao.objects.get(nome="Turismo/Hotelaria")

    def test_envio_cria_solicitacao_pendente(self):
        resposta = self.client.post(
            reverse("vagas:divulgar"), dados_formulario_empresa(self.municipio, self.area)
        )
        self.assertRedirects(resposta, reverse("vagas:divulgar_enviada"))

        solicitacao = SolicitacaoVaga.objects.get()
        self.assertEqual(solicitacao.situacao, SolicitacaoVaga.Situacao.PENDENTE)
        self.assertTrue(solicitacao.codigo_acompanhamento.startswith("VLS-"))
        self.assertEqual(len(solicitacao.codigo_acompanhamento), 13)
        self.assertEqual(str(solicitacao.salario), "1600.00")
        self.assertNotEqual(solicitacao.ip_hash, "")
        # Nada é publicado antes da moderação
        self.assertFalse(Vaga.objects.exists())

        # A página de confirmação mostra o código
        confirmacao = self.client.get(reverse("vagas:divulgar_enviada"))
        self.assertContains(confirmacao, solicitacao.codigo_acompanhamento)

    def test_sem_aceite_do_termo_nao_envia(self):
        dados = dados_formulario_empresa(self.municipio, self.area)
        del dados["aceite_termo"]
        resposta = self.client.post(reverse("vagas:divulgar"), dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(SolicitacaoVaga.objects.exists())

    def test_honeypot_preenchido_bloqueia(self):
        dados = dados_formulario_empresa(self.municipio, self.area, url_site="http://spam.example")
        self.client.post(reverse("vagas:divulgar"), dados)
        self.assertFalse(SolicitacaoVaga.objects.exists())

    def test_cnpj_invalido_bloqueia(self):
        dados = dados_formulario_empresa(self.municipio, self.area, cnpj="11.222.333/0001-00")
        resposta = self.client.post(reverse("vagas:divulgar"), dados)
        self.assertContains(resposta, "CNPJ inválido")
        self.assertFalse(SolicitacaoVaga.objects.exists())

    def test_cnpj_valido_e_formatado(self):
        dados = dados_formulario_empresa(self.municipio, self.area, cnpj="11222333000181")
        self.client.post(reverse("vagas:divulgar"), dados)
        self.assertEqual(SolicitacaoVaga.objects.get().cnpj, "11.222.333/0001-81")

    @override_settings(LIMITE_SOLICITACOES_POR_HORA=2)
    def test_limite_de_envios_por_ip(self):
        dados = dados_formulario_empresa(self.municipio, self.area)
        self.client.post(reverse("vagas:divulgar"), dados)
        self.client.post(reverse("vagas:divulgar"), dados)
        resposta = self.client.post(reverse("vagas:divulgar"), dados)
        self.assertEqual(resposta.status_code, 429)
        self.assertEqual(SolicitacaoVaga.objects.count(), 2)

        # Outro IP continua podendo enviar
        self.client.post(reverse("vagas:divulgar"), dados, REMOTE_ADDR="10.0.0.99")
        self.assertEqual(SolicitacaoVaga.objects.count(), 3)

    def test_acompanhar_pelo_codigo(self):
        solicitacao = SolicitacaoVaga.objects.create(
            titulo="Garçom",
            descricao="Atendimento",
            municipio=self.municipio,
            area=self.area,
            empresa="Restaurante",
            tipo_contrato=TipoContrato.TEMPORARIO,
            escolaridade=Escolaridade.NAO_EXIGE,
            jornada="Fins de semana",
            forma_candidatura="Telefone (84) 3333-3333",
            aceite_termo=True,
        )
        codigo_minusculo = solicitacao.codigo_acompanhamento.lower()
        resposta = self.client.get(reverse("vagas:acompanhar"), {"codigo": codigo_minusculo})
        self.assertContains(resposta, "Pendente")
        self.assertContains(resposta, "Garçom")

        resposta = self.client.get(reverse("vagas:acompanhar"), {"codigo": "VLS-0000-0000"})
        self.assertContains(resposta, "Nenhuma solicitação encontrada")


class ComandoExpirarVagasTests(TestCase):
    """Comando de manutenção: expira vagas e anonimiza recusadas antigas."""

    @classmethod
    def setUpTestData(cls):
        cls.municipio = Municipio.objects.get(slug="goianinha")
        cls.area = AreaAtuacao.objects.get(nome="Indústria")

    def _rodar_comando(self):
        saida = StringIO()
        call_command("expirar_vagas", stdout=saida)
        return saida.getvalue()

    def test_marca_vagas_vencidas_como_expiradas(self):
        hoje = timezone.localdate()
        vencida = criar_vaga(self.municipio, self.area, data_expiracao=hoje - timedelta(days=1))
        valida = criar_vaga(self.municipio, self.area, data_expiracao=hoje)
        encerrada = criar_vaga(
            self.municipio,
            self.area,
            data_expiracao=hoje - timedelta(days=5),
            situacao=Vaga.Situacao.ENCERRADA,
        )

        saida = self._rodar_comando()

        vencida.refresh_from_db()
        valida.refresh_from_db()
        encerrada.refresh_from_db()
        self.assertEqual(vencida.situacao, Vaga.Situacao.EXPIRADA)
        self.assertEqual(valida.situacao, Vaga.Situacao.ABERTA)
        self.assertEqual(encerrada.situacao, Vaga.Situacao.ENCERRADA)
        self.assertIn("Vagas marcadas como expiradas: 1", saida)

    def test_anonimiza_recusadas_com_mais_de_180_dias(self):
        def nova_solicitacao(situacao, dias_desde_moderacao):
            return SolicitacaoVaga.objects.create(
                titulo="Vaga",
                descricao="Descrição",
                municipio=self.municipio,
                area=self.area,
                empresa="Empresa",
                tipo_contrato=TipoContrato.CLT,
                escolaridade=Escolaridade.MEDIO,
                jornada="44h",
                forma_candidatura="email@empresa.com",
                cnpj="11.222.333/0001-81",
                nome_responsavel="João",
                email_responsavel="joao@empresa.com",
                telefone_responsavel="(84) 98888-0000",
                aceite_termo=True,
                situacao=situacao,
                moderado_em=timezone.now() - timedelta(days=dias_desde_moderacao),
            )

        antiga = nova_solicitacao(SolicitacaoVaga.Situacao.RECUSADA, 200)
        recente = nova_solicitacao(SolicitacaoVaga.Situacao.RECUSADA, 10)
        aprovada_antiga = nova_solicitacao(SolicitacaoVaga.Situacao.APROVADA, 200)

        self._rodar_comando()

        antiga.refresh_from_db()
        recente.refresh_from_db()
        aprovada_antiga.refresh_from_db()

        self.assertEqual(antiga.nome_responsavel, "")
        self.assertEqual(antiga.email_responsavel, "")
        self.assertEqual(antiga.telefone_responsavel, "")
        self.assertEqual(antiga.cnpj, "")
        self.assertIsNotNone(antiga.dados_anonimizados_em)
        self.assertEqual(antiga.titulo, "Vaga")  # dados da vaga são mantidos

        self.assertEqual(recente.email_responsavel, "joao@empresa.com")
        self.assertEqual(aprovada_antiga.email_responsavel, "joao@empresa.com")


class ComandoPopularDemoTests(TestCase):
    """O comando de demonstração cria operadores e cerca de 20 vagas."""

    def test_popular_demo(self):
        call_command("popular_demo", stdout=StringIO())
        self.assertEqual(Vaga.objects.count(), 20)
        self.assertEqual(SolicitacaoVaga.objects.count(), 3)
        self.assertTrue(
            self.client.login(username="operador.canguaretama", password="Demo@Vagas2026")
        )


class ValidadorCnpjTests(TestCase):
    """Validação de CNPJ numérico e alfanumérico."""

    def test_cnpj_numerico(self):
        self.assertTrue(cnpj_valido("11.222.333/0001-81"))
        self.assertTrue(cnpj_valido("11222333000181"))
        self.assertFalse(cnpj_valido("11.222.333/0001-82"))

    def test_cnpj_alfanumerico(self):
        self.assertTrue(cnpj_valido("12.ABC.345/01DE-35"))
        self.assertTrue(cnpj_valido("12.abc.345/01de-35"))
        self.assertFalse(cnpj_valido("12.ABC.345/01DE-36"))

    def test_cnpj_invalidos(self):
        self.assertFalse(cnpj_valido("00.000.000/0000-00"))
        self.assertFalse(cnpj_valido("123"))
        self.assertFalse(cnpj_valido(""))
