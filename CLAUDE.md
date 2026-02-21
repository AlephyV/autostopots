# 🤖 Contexto do Projeto: Auto-StopotS (Bot com IA)

## 📌 Visão Geral
O objetivo deste projeto é construir um bot automatizado para o jogo web "StopotS" (jogo de adedanha/stop online). O bot deve ler a tela do jogo para identificar a letra da rodada e as categorias, enviar esses dados para uma API de LLM (Inteligência Artificial) para gerar respostas válidas, e preencher os campos do jogo automaticamente simulando comportamento humano para evitar detecção (anti-cheat).

## 🛠️ Stack Tecnológica
* **Linguagem:** Python 3
* **Manipulação Web (Scraping/Automação):** Playwright (modo assíncrono ou síncrono, priorizando simulação de eventos reais de teclado/mouse).
* **Camada de Inteligência:** API de LLM (Gemini ou OpenAI) com estruturação de prompt para retornar JSON.
* **Interface Gráfica (GUI):** A definir (CustomTkinter ou PyQt) para envelopar o script.

## 🏗️ Arquitetura em 3 Camadas
O projeto segue uma arquitetura modularizada:
1.  **GUI (`gui/interface.py`):** Interface para o usuário iniciar/parar o bot, inserir API Keys e ver logs.
2.  **Manipulator (`core/manipulator.py`):** Controla o navegador via Playwright. Responsável por mapear o DOM, ler os elementos e injetar texto (usando digitação sequencial, não apenas alteração de `.value`) para contornar validações do front-end do jogo.
3.  **Intelligence (`core/intelligence.py`):** Recebe a letra e a lista de categorias. Monta o prompt, faz a requisição HTTP para a API da IA e devolve um dicionário (JSON) validado com as palavras correspondentes.

## 🔍 Estrutura do DOM Conhecida (Extraída de stop1.html)
Classes CSS são dinâmicas (ex: `.jsx-42179c218931b741`), então usamos seletores estruturais.

### Seletores Mapeados
| Elemento | Seletor CSS | Estrutura HTML |
|---|---|---|
| **Letra da rodada** | `div.maskLetter p` | `div.letter > div.maskLetter > span > p.animate` → `"D"` |
| **Nome da categoria** | `label legend p` | `div.answer > label > legend > p` → `"Fruta"` |
| **Nome completo (tooltip)** | `label .tooltip p` | `div.answer > label > div.tooltip > p` → `"Personagem de Desenho Animado"` |
| **Input de resposta** | `#inputText-N` | `div.answer > label > input#inputText-0` (sequencial: 0, 1, 2...) |
| **Rodada** | `span.rounds p strong` | `span.rounds > p > strong` → `"1"` (de "1/8") |

### Hierarquia de uma Categoria
```html
<div class="... answer">
  <label>
    <!-- opcional, só em categorias abreviadas (PDA, PÁF) -->
    <div class="... tooltip"><p>Nome Completo da Categoria</p></div>
    <legend><p>Nome Curto</p></legend>
    <input id="inputText-N" maxlength="20" autocomplete="off" type="text">
  </label>
</div>
```

## ⚠️ Development Rules
1.  **All code in English:** Function names, variable names, comments, and docstrings must be in English. **Exception:** user-facing print messages (logs shown in terminal) must be in pt-BR.
2.  **Anti-Cheat focus:** Browser interactions must fire real events (e.g. use `locator.press_sequentially()` with delay, never `locator.fill()`).
3.  **Strict modularity:** `manipulator.py` must not know about the AI API. `intelligence.py` must not know about HTML/Playwright. `main.py` orchestrates.
4.  **Error resilience:** The bot must not crash if the AI returns a wrong letter or the round timer expires mid-typing.
5.  **Structured AI responses:** The AI prompt must enforce JSON output, mapping category names directly to generated words.

## 🚀 Status Atual
Estamos na **Fase 1: Prova de Conceito (PoC) do Manipulador**. O foco atual é criar o script Playwright que entra na sala, lê a letra e os temas, e consegue digitar nos inputs correspondentes.
