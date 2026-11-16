/*
 * Modo de alto contraste.
 *
 * - O botão "Alto contraste" (barra gov.br) liga e desliga a classe
 *   "alto-contraste" no elemento <html>.
 * - A preferência fica guardada no localStorage do navegador.
 * - Este arquivo é carregado no <head> para aplicar o modo antes de a
 *   página aparecer (evita a "piscada" de cores).
 */
(function () {
  "use strict";

  var CHAVE = "vls-alto-contraste";
  var raiz = document.documentElement;

  // Lê a preferência salva (o localStorage pode estar bloqueado)
  function lerPreferencia() {
    try {
      return window.localStorage.getItem(CHAVE) === "1";
    } catch (erro) {
      return false;
    }
  }

  // Salva a preferência, ignorando falhas (ex.: navegação anônima)
  function salvarPreferencia(ativo) {
    try {
      window.localStorage.setItem(CHAVE, ativo ? "1" : "0");
    } catch (erro) {
      // Sem localStorage, o modo vale só para esta página
    }
  }

  // Liga/desliga o modo e atualiza o estado do botão para leitores de tela
  function aplicar(ativo) {
    raiz.classList.toggle("alto-contraste", ativo);
    var botao = document.getElementById("botao-alto-contraste");
    if (botao) {
      botao.setAttribute("aria-pressed", ativo ? "true" : "false");
    }
  }

  // 1) Aplica imediatamente, antes de a página ser desenhada
  aplicar(lerPreferencia());

  // 2) Quando a página terminar de carregar, liga o clique do botão
  document.addEventListener("DOMContentLoaded", function () {
    aplicar(lerPreferencia());

    var botao = document.getElementById("botao-alto-contraste");
    if (!botao) {
      return;
    }

    botao.addEventListener("click", function () {
      var ativo = !raiz.classList.contains("alto-contraste");
      aplicar(ativo);
      salvarPreferencia(ativo);
    });
  });
})();
