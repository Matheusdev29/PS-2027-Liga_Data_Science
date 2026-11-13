# PS-2027-Liga_Data_Science

# Plataforma Digital para Processo Seletivo
Uma aplicação web interativa desenvolvida com Streamlit para gerenciar e otimizar todas as etapas de um processo seletivo.

# Sobre o Projeto
A Plataforma Digital para Processo Seletivo centraliza o recebimento de candidaturas, acompanhamento de etapas, triagem e comunicação com candidatos em uma interface simples, rápida e responsiva.

###  Tecnologias Utilizadas

* **Python**
* **Streamlit**
* **Pandas** (para manipulação de dados)
* **SQLite** (para armazenamento dos candidatos)

## 📅 Cronograma de Desenvolvimento (22/08 a 31/10)

| Semana | Período | Principais Entregas & Foco |
| :--- | :--- | :--- |
| **Semana 1** | 22/08 – 28/08 | Construir o esqueleto do app multipage. |
| **Semana 2** | 29/08 – 04/09 | Desenvolver o formulário de inscrição completo. |
| **Semana 3** |	05/09 – 11/09	| Implementar o algoritmo de score de fit cultural. |
| **Semana 4** |	12/09 – 18/09 |	Integrar persistência de dados na nuvem via Google Sheets. |
| **Semana 5** |	19/09 – 25/09 |	Testes internos do MVP. |
| **Semana 6** |	26/09 – 02/10 |	Desenvolver o dashboard de análise dos candidatos. |
| **Semana 7** |	03/10 – 09/10 |	Construir o painel de gestão completo. |
| **Semana 8** |	10/10 – 16/10 |	Preparar o app para produção. |
| **Semana 9** |	17/10 – 23/10 |	Testes finais de aceitação |
---

# Como Executar o Projeto
* **instale streamlit:**
  Bash
    pip install streamlit
*  **Crie um ambiente virtual (opcional, mas recomendado, criar somente uma vez):**
  Bash
   * python -m venv venv
   * source venv/bin/activate  # Linux/Mac
   * venv\Scripts\activate     # Windows
   *para desativar ambiente virtual **deactivate**
* **Clone o repositório:**
  Bash
    git clone https://github.com/Matheusdev29/PS-2027-Liga_Data_Science.git
    cd PS-2027-Liga_Data_Science
  
*  **Instale as dependências:**
  Bash
   pip install -r requirements.txt
  
 * **Execute a aplicação:**
  Bash
    streamlit run app.py

# Score de candidatos - Liga de Data Science
 
Pontua candidatos por área (RH, Projetos, Marketing, Training) e calcula o fit com os valores da liga a partir das respostas do formulário.
 
## Regras de pontuação
 
As perguntas são identificadas pela **posição da coluna na planilha** (índice começando em 0, com a letra da coluna entre parênteses). A nota é o número no início da resposta: `5 - Concordo totalmente` vale 5; resposta vazia ou sem número vale 0.
 
### 1. Quais perguntas somam em cada área
 
Cada área soma 3 perguntas de escala 1–5, então o máximo é **15 pontos**.
 
| Área | Colunas que somam | Máximo |
|---|---|---|
| RH | 32 (AG), 37 (AL), 39 (AN) | 15 |
| Projetos | 33 (AH), 35 (AJ), 43 (AR) | 15 |
| Marketing | 31 (AF), 34 (AI), 38 (AM) | 15 |
| Training | 36 (AK), 40 (AO), 42 (AQ) | 15 |
 
### 2. Penalizações
 
Cada resposta incompatível com a área tira **2 pontos** dessa área. A nota nunca fica abaixo de 0 (o limite é aplicado depois de cada pergunta). As penalizações são aplicadas aos pontos da área **antes** da área sugerida e do score final.
 
| Área | Coluna | Resposta que penaliza | Desconto |
|---|---|---|---|
| RH | 32 (AG) | 1 | −2 por resposta |
| RH | 37 (AL) | 1 | −2 por resposta |
| RH | 39 (AN) | 1 | −2 por resposta |
| Projetos | 35 (AJ) | 1 | −2 por resposta |
| Projetos | 43 (AR) | 1 ou 2 | −2 por resposta |
| Marketing | 34 (AI) | 1 | −2 por resposta |
| Marketing | 38 (AM) | 1 ou 2 | −2 por resposta |
| Training | 40 (AO) | 2 | −2 por resposta |
| Training | 42 (AQ) | 1 ou 2 | −2 por resposta |
 
### 3. Fit de valores (corte)
 
Soma de 10 perguntas de escala 1–5 (máximo **50** pontos): 9 (J), 10 (K), 11 (L), 13 (N), 14 (O), 15 (P), 16 (Q), 18 (S), 19 (T), 20 (U).
 
| Pontos | Resultado |
|---|---|
| 30 ou mais | Fit: **Sim** |
| menos de 30 | Fit: **Não** |
 
### 4. Área sugerida
 
É a área com mais pontos **depois** das penalizações. Em caso de empate vale a primeira na ordem RH, Projetos, Marketing, Training; `areas_empatadas` lista todas as que empataram. Se todas as áreas ficarem com 0, não há área sugerida.
 
### Onde mudar as regras
 
Em `score.py`: `COLUNAS_AREAS` (perguntas por área), `REGRAS_PENALIZACAO` (penalizações), `COLUNAS_VALORES` (perguntas de valores) e, em `Config`, `penalidade` e `fit_minimo`. Ao mudar qualquer uma, atualize as tabelas acima e rode `pytest`.
 
