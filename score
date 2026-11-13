"""score.py - Pontuação de candidatos da Liga de Data Science.

Módulo puro (sem pandas, sem print, sem Colab) com a mesma lógica do notebook:

1. Nota objetiva por área (RH, Projetos, Marketing, Training): soma de 3 perguntas
   de escala 1-5 (máximo 15 por área).
2. Penalizações por respostas incompatíveis com a área (-2 por resposta ruim,
   sem deixar a nota negativa).
3. Score final 0-100 por área, via LLM (Groq/Llama) com o prompt original; sem
   LLM, usa um avaliador local (50% nota objetiva + 50% palavras-chave do texto).
4. Fit de valores: soma das 10 perguntas de valores (máx. 50); "Sim" se >= 30.

As perguntas são identificadas pelo NÚMERO DA COLUNA da planilha (os mesmos
índices do notebook). Uso:

    from score import score_candidate, candidato_de_linha

    candidato = {
        "respostas": {32: "5 - Concordo totalmente", 37: "4", ...},  # índice -> resposta
        "texto": "respostas dissertativas juntas",
    }
    resultado = score_candidate(candidato)

    # A partir de uma linha da planilha (lista na ordem das colunas):
    candidato = candidato_de_linha(linha, colunas_texto=[44, 45, 46])
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

# --------------------------------------------------------------------------- #
# Estrutura do formulário (índices de coluna do collab)
# --------------------------------------------------------------------------- #

AREAS = ("rh", "projetos", "marketing", "training")

NOMES_AREAS = {
    "rh": "RH",
    "projetos": "Projetos",
    "marketing": "Marketing",
    "training": "Training",
}

MAX_PONTOS_OBJETIVOS = 15  # 3 perguntas x nota máxima 5

# Colunas das perguntas objetivas por área.
COLUNAS_AREAS = {
    "rh": [32, 37, 39],
    "projetos": [33, 35, 43],
    "marketing": [31, 34, 38],
    "training": [36, 40, 42],
}

# As 10 perguntas de valores da liga.
COLUNAS_VALORES = [9, 10, 11, 13, 14, 15, 16, 18, 19, 20]

# Colunas dissertativas (colunas_interesse do notebook), enviadas à LLM como texto.
COLUNAS_TEXTO = [6, 7, 8, 27, 28, 29, 30]

# Penalizações: (área, coluna da pergunta, respostas ruins). Cada resposta ruim
# encontrada tira `penalidade` pontos da área.
REGRAS_PENALIZACAO = [
    ("rh", 32, [1]),
    ("rh", 37, [1]),
    ("rh", 39, [1]),
    ("projetos", 35, [1]),
    ("projetos", 43, [1, 2]),
    ("marketing", 34, [1]),
    ("marketing", 38, [1, 2]),
    ("training", 40, [2]),
    ("training", 42, [1, 2]),
]

# Definições das áreas (idênticas ao prompt do notebook).
DEFINICOES_AREAS = {
    "rh": (
        "Gestão de pessoas, empatia, organização, liderança, mediação, comunicação, "
        "lidar com pessoas, gestão de conflitos, escuta ativa, clima organizacional, "
        "cultura da liga, recrutamento, feedback construtivo, engajamento, mediação, "
        "desenvolvimento humano, trabalho em equipe."
    ),
    "projetos": (
        "Habilidade técnica, lógica, foco em resolver problemas, organizar, liderar, "
        "calma, entrega de resultados, visão analítica, otimização, resolução de "
        "problemas, eficiência, prazos."
    ),
    "marketing": (
        "Criatividade, design, redes sociais, branding, marketing, instagram, "
        "identidade visual, engajamento digital, copywriting, storytelling, artes para "
        "redes sociais, comunicação visual, prospecção, parcerias."
    ),
    "training": (
        "Didática, ensino, paciência, vontade de compartilhar conhecimento, ajudar, "
        "aprender, facilitação, mentorias, material didático, capacitação, "
        "nivelamento técnico, instrução."
    ),
}

# Palavras-chave do avaliador local (derivadas das definições acima).
PALAVRAS_CHAVE = {
    "rh": [
        "pessoas", "empatia", "lideranca", "mediacao", "comunicacao", "conflito",
        "escuta", "clima", "cultura", "recrutamento", "feedback", "engajamento",
        "desenvolvimento humano", "equipe", "organizacao",
    ],
    "projetos": [
        "tecnica", "logica", "problema", "organizar", "calma", "resultado",
        "analitic", "otimiza", "eficiencia", "prazo", "entrega", "dados",
    ],
    "marketing": [
        "criatividade", "design", "redes sociais", "branding", "marketing",
        "instagram", "identidade visual", "copywriting", "storytelling", "arte",
        "comunicacao visual", "prospeccao", "parceria",
    ],
    "training": [
        "didatica", "ensino", "ensinar", "paciencia", "compartilhar", "ajudar",
        "aprender", "facilitacao", "mentoria", "material didatico", "capacitacao",
        "nivelamento", "instrucao",
    ],
}


@dataclass
class Config:
    """Parâmetros ajustáveis do cálculo."""

    penalidade: float = 2.0             # pontos por resposta ruim
    fit_minimo: int = 30                # soma mínima dos valores para "Sim"
    peso_objetivo: float = 0.5          # avaliador local: 50% objetivo / 50% texto
    peso_texto: float = 0.5
    modelo: str = "llama-3.3-70b-versatile"
    api_base: str = "https://api.groq.com/openai/v1"
    temperatura: float = 0.1
    max_retries: int = 2


# --------------------------------------------------------------------------- #
# Utilitários
# --------------------------------------------------------------------------- #

def _normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar palavras-chave."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def _vazio(resposta: Any) -> bool:
    if resposta is None:
        return True
    try:
        return resposta != resposta  # NaN
    except Exception:
        return False


def extrair_nota(resposta: Any) -> int:
    """Extrai o primeiro número do texto (ex.: '5 - Concordo totalmente' -> 5).

    Resposta vazia/NaN ou sem número vale 0, como no notebook.
    """
    if _vazio(resposta):
        return 0
    achado = re.search(r"\d+", str(resposta))
    return int(achado.group()) if achado else 0


def _resposta(respostas: dict, coluna: int) -> Any:
    """Busca a resposta pela coluna, aceitando chave int ou str."""
    if coluna in respostas:
        return respostas[coluna]
    return respostas.get(str(coluna))


_NLP = None  # modelo spaCy carregado sob demanda


def _carregar_spacy():
    """Carrega pt_core_news_sm uma única vez; None se spaCy/modelo não existirem."""
    global _NLP
    if _NLP is None:
        try:
            import spacy
            _NLP = spacy.load("pt_core_news_sm")
        except Exception:
            _NLP = False
    return _NLP or None


def preprocessar_texto(texto: Any, usar_spacy: bool = True) -> str:
    """Mesmo pré-processamento do notebook: minúsculas, sem acentos, só letras,
    lematização e remoção de stopwords (spaCy pt_core_news_sm).

    Sem spaCy instalado, faz só a limpeza (minúsculas, sem acentos, só letras).
    """
    if _vazio(texto):
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto).lower())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-zà-ú\s]", " ", sem_acento)
    nlp = _carregar_spacy() if usar_spacy else None
    if nlp is None:
        return " ".join(limpo.split())
    return " ".join(t.lemma_ for t in nlp(limpo) if not t.is_stop)


def candidato_de_linha(
    valores: Sequence[Any],
    colunas_texto: Optional[Sequence[int]] = None,
    preprocessar: bool = True,
) -> dict:
    """Monta o candidato a partir de uma linha da planilha (lista por posição).

    O texto vem de `colunas_texto` (padrão: COLUNAS_TEXTO, as colunas_interesse do
    notebook), pré-processado como no notebook quando `preprocessar=True`.

    Exemplo com pandas:
        candidato_de_linha(row.tolist())
    """
    usadas = set(COLUNAS_VALORES)
    for colunas in COLUNAS_AREAS.values():
        usadas.update(colunas)
    respostas = {i: valores[i] for i in usadas if i < len(valores)}
    colunas_texto = COLUNAS_TEXTO if colunas_texto is None else colunas_texto
    partes = []
    for i in colunas_texto:
        if i < len(valores) and not _vazio(valores[i]):
            partes.append(preprocessar_texto(valores[i]) if preprocessar else str(valores[i]))
    return {"respostas": respostas, "texto": " ".join(p for p in partes if p)}


# --------------------------------------------------------------------------- #
# 1) Nota objetiva por área + 2) Penalizações
# --------------------------------------------------------------------------- #

# Regras de penalização agrupadas por área: {area: [(coluna, [respostas ruins])]}
REGRAS_POR_AREA: dict[str, list[tuple[int, list[int]]]] = {a: [] for a in AREAS}
for _area, _coluna, _ruins in REGRAS_PENALIZACAO:
    REGRAS_POR_AREA[_area].append((_coluna, _ruins))


def _como_numero(valor: float) -> float:
    """8.0 -> 8 (mantém decimais de verdade, como 7.5)."""
    return int(valor) if float(valor).is_integer() else valor


def pontos_area(respostas: dict, perguntas_da_area: Sequence[int]) -> int:
    """Soma as notas das perguntas da área (máx. 15 com 3 perguntas de escala 1-5).

    `respostas` é {coluna: resposta}; `perguntas_da_area` é a lista de colunas
    (ex.: COLUNAS_AREAS["rh"]). Resposta vazia ou sem número vale 0.
    """
    return sum(extrair_nota(_resposta(respostas, c)) for c in perguntas_da_area)


def _aplicar_regras(
    pontos: float,
    respostas: dict,
    regras: Sequence[tuple[int, Sequence[int]]],
    penalidade: float,
    area: str = "",
) -> tuple[float, list[dict]]:
    """Aplica as regras de uma área e devolve (pontos, penalizações aplicadas).

    Como no notebook, a nota é limitada a >= 0 depois de cada pergunta e a
    resposta é considerada ruim se o texto COMEÇA com o número da regra.
    """
    aplicadas: list[dict] = []
    for coluna, ruins in regras:
        resposta = _resposta(respostas, coluna)
        texto_resp = "nan" if _vazio(resposta) else str(resposta).strip()
        for ruim in ruins:
            if texto_resp.startswith(str(ruim)):
                pontos -= penalidade
                aplicadas.append({
                    "area": NOMES_AREAS.get(area, area),
                    "coluna": coluna,
                    "resposta": texto_resp,
                    "pontos": -penalidade,
                })
        pontos = max(pontos, 0)
    return _como_numero(pontos), aplicadas


def penalizar(
    pontos: float,
    respostas: dict,
    regras: Sequence[tuple[int, Sequence[int]]],
    penalidade: float = 2,
) -> float:
    """Desconta `penalidade` pontos por resposta ruim e devolve a nota da área.

    `regras` é uma lista de (coluna, [respostas ruins]); ex. a regra
    (43, [1, 2]) penaliza quem respondeu "1..." ou "2..." na coluna 43.
    A nota nunca fica negativa.
    """
    return _aplicar_regras(pontos, respostas, regras, penalidade)[0]


def calcular_pontos_objetivos(respostas: dict, config: Optional[Config] = None) -> dict:
    """Pontos objetivos por área, antes e depois das penalizações.

    Returns:
        {"brutos": {area: pts}, "finais": {area: pts}, "penalizacoes": [...]}
    """
    config = config or Config()
    brutos = {area: pontos_area(respostas, COLUNAS_AREAS[area]) for area in AREAS}
    finais: dict[str, float] = {}
    penalizacoes: list[dict] = []
    for area in AREAS:
        finais[area], aplicadas = _aplicar_regras(
            brutos[area], respostas, REGRAS_POR_AREA[area], config.penalidade, area
        )
        penalizacoes.extend(aplicadas)
    return {"brutos": brutos, "finais": finais, "penalizacoes": penalizacoes}


# --------------------------------------------------------------------------- #
# 3) Fit de valores
# --------------------------------------------------------------------------- #

def calcular_fit_valores(respostas: dict, config: Optional[Config] = None) -> dict:
    """Soma as 10 perguntas de valores (máx. 50); 'Sim' se >= fit_minimo."""
    config = config or Config()
    pontos = pontos_area(respostas, COLUNAS_VALORES)
    return {
        "pontos": pontos,
        "maximo": 5 * len(COLUNAS_VALORES),
        "minimo": config.fit_minimo,
        "fit": "Sim" if pontos >= config.fit_minimo else "Não",
        "aprovado": pontos >= config.fit_minimo,
    }


def fit_valores(respostas: dict, config: Optional[Config] = None) -> bool:
    """True se a soma das 10 perguntas de valores for >= fit_minimo (padrão 30)."""
    return calcular_fit_valores(respostas, config)["aprovado"]


def calcular_score(respostas: dict, config: Optional[Config] = None) -> dict:
    """Resultado objetivo completo do candidato, sem LLM e sem texto.

    Returns:
        {
          "pontos": {"rh", "projetos", "marketing", "training"} já penalizados,
          "pontos_brutos": os mesmos pontos antes das penalizações,
          "penalizacoes": [{"area", "coluna", "resposta", "pontos"}, ...],
          "area_sugerida": nome da área com mais pontos (None se todas forem 0),
          "areas_empatadas": nomes das áreas no topo (mais de uma = empate; em
                             empate, area_sugerida é a primeira em RH, Projetos,
                             Marketing, Training),
          "fit": bool,
          "fit_pontos": soma das perguntas de valores (0-50),
        }
    """
    config = config or Config()
    objetivos = calcular_pontos_objetivos(respostas, config)
    pontos = objetivos["finais"]

    topo = max(pontos.values())
    empatadas = [NOMES_AREAS[a] for a in AREAS if pontos[a] == topo] if topo > 0 else []
    fit = calcular_fit_valores(respostas, config)

    return {
        "pontos": dict(pontos),
        "pontos_brutos": dict(objetivos["brutos"]),
        "penalizacoes": objetivos["penalizacoes"],
        "area_sugerida": empatadas[0] if empatadas else None,
        "areas_empatadas": empatadas,
        "fit": fit["aprovado"],
        "fit_pontos": fit["pontos"],
    }


# --------------------------------------------------------------------------- #
# 4) Score final por área (LLM do notebook, com fallback local)
# --------------------------------------------------------------------------- #

def montar_prompt(pontos: dict[str, float], texto: str) -> str:
    def fmt(area: str) -> str:
        p = pontos[area]
        return f"{int(p) if float(p).is_integer() else p}/{MAX_PONTOS_OBJETIVOS}"

    return f"""
Atue como um Especialista em Recrutamento para uma Liga de Data Science.
Sua missão é avaliar o perfil do candidato abaixo e atribuir uma nota de 0 a 100 para CADA uma das 4 áreas possíveis.

Para formar a sua nota final (0-100), você DEVE ponderar duas coisas com igual importância:
1. A pontuação objetiva que o candidato fez no teste de afinidade (de 0 a {MAX_PONTOS_OBJETIVOS} pontos por área).
2. A análise semântica das respostas dissertativas dele, baseando-se estritamente nas definições abaixo.

DEFINIÇÕES DAS ÁREAS (O QUE BUSCAR NO TEXTO DISSERTATIVO):
1. RH: {DEFINICOES_AREAS['rh']}
2. PROJETOS: {DEFINICOES_AREAS['projetos']}
3. MARKETING: {DEFINICOES_AREAS['marketing']}
4. TRAINING: {DEFINICOES_AREAS['training']}

PONTUAÇÃO OBJETIVA DO CANDIDATO (MÁXIMO {MAX_PONTOS_OBJETIVOS} PONTOS POR ÁREA):
- RH: {fmt('rh')}
- Projetos: {fmt('projetos')}
- Marketing: {fmt('marketing')}
- Training: {fmt('training')}

DADOS DISSERTATIVOS DO CANDIDATO:
{texto}

TAREFA:
Analise a pontuação objetiva junto com o texto (buscando as palavras-chave das definições) e atribua um Score final (0-100) para cada área.

RESPOSTA OBRIGATÓRIA EM JSON (SEM MARKDOWN):
{{
    "score_rh": 0,
    "score_projetos": 0,
    "score_marketing": 0,
    "score_training": 0,
    "area_principal": "Nome da área com maior nota",
    "justificativa": "Explicação breve unindo a nota objetiva e as características encontradas no texto"
}}
""".strip()


def criar_llm(config: Optional[Config] = None):
    """Cria o cliente da LLM (Groq via API compatível com OpenAI).

    Retorna None se não houver GROQ_API_KEY ou langchain_openai; nesse caso o
    módulo usa o avaliador local.
    """
    config = config or Config()
    chave = os.environ.get("GROQ_API_KEY")
    if not chave:
        return None
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None
    return ChatOpenAI(
        openai_api_base=config.api_base,
        openai_api_key=chave,
        model_name=config.modelo,
        temperature=config.temperatura,
        max_retries=config.max_retries,
    )


def extrair_json(conteudo: str) -> dict:
    """Extrai o JSON da resposta da LLM, tolerando cercas de markdown."""
    conteudo = (conteudo or "").strip()
    if "```json" in conteudo:
        conteudo = conteudo.split("```json")[1].split("```")[0]
    elif "```" in conteudo:
        conteudo = conteudo.split("```")[1].split("```")[0]
    try:
        return json.loads(conteudo)
    except json.JSONDecodeError:
        achado = re.search(r"\{.*\}", conteudo, re.DOTALL)
        if not achado:
            raise
        return json.loads(achado.group(0))


def _contar_palavras_chave(texto_norm: str, area: str) -> int:
    return sum(1 for p in PALAVRAS_CHAVE[area] if p in texto_norm)


def pontuar_areas_local(pontos: dict[str, float], texto: str, config: Config) -> dict:
    """Avaliador sem LLM: objetivo (0-15 -> 0-100) + cobertura de palavras-chave."""
    texto_norm = _normalizar(texto)
    scores: dict[str, float] = {}
    for area in AREAS:
        obj = pontos[area] / MAX_PONTOS_OBJETIVOS * 100
        # 4 palavras-chave distintas já indicam forte aderência
        txt = _clamp(_contar_palavras_chave(texto_norm, area) / 4 * 100, 0, 100)
        scores[area] = round(_clamp(config.peso_objetivo * obj + config.peso_texto * txt, 0, 100), 1)
    principal = max(scores, key=scores.get)
    return {
        "scores": scores,
        "area_principal": NOMES_AREAS[principal],
        "justificativa": (
            "Avaliação local: nota objetiva e palavras-chave do texto com pesos "
            f"{config.peso_objetivo:.0%}/{config.peso_texto:.0%}."
        ),
        "origem": "local",
    }


def pontuar_areas_llm(pontos: dict[str, float], texto: str, llm: Any) -> dict:
    """Chama a LLM com o prompt do notebook e devolve os scores 0-100 por área."""
    resposta = llm.invoke(montar_prompt(pontos, texto))
    dados = extrair_json(str(getattr(resposta, "content", resposta)))
    scores = {
        "rh": _clamp(float(dados.get("score_rh", 0) or 0), 0, 100),
        "projetos": _clamp(float(dados.get("score_projetos", 0) or 0), 0, 100),
        "marketing": _clamp(float(dados.get("score_marketing", 0) or 0), 0, 100),
        "training": _clamp(float(dados.get("score_training", 0) or 0), 0, 100),
    }
    return {
        "scores": scores,
        "area_principal": dados.get("area_principal") or NOMES_AREAS[max(scores, key=scores.get)],
        "justificativa": dados.get("justificativa", ""),
        "origem": "llm",
    }


def pontuar_areas(
    pontos: dict[str, float], texto: str, llm: Any = None, config: Optional[Config] = None
) -> dict:
    """Usa a LLM quando disponível; se ela falhar, cai no avaliador local."""
    config = config or Config()
    if llm is not None:
        try:
            return pontuar_areas_llm(pontos, texto, llm)
        except Exception as erro:  # rede, JSON inválido, limite de taxa...
            resultado = pontuar_areas_local(pontos, texto, config)
            resultado["justificativa"] += f" (LLM falhou: {type(erro).__name__})"
            return resultado
    return pontuar_areas_local(pontos, texto, config)


# --------------------------------------------------------------------------- #
# API principal
# --------------------------------------------------------------------------- #

def score_candidate(
    candidato: dict,
    llm: Any = None,
    config: Optional[Config] = None,
    usar_llm_padrao: bool = True,
) -> dict:
    """Avalia um candidato.

    Args:
        candidato: dict com
            - "respostas": {coluna: resposta} das perguntas objetivas e de valores
              (chave int ou str; ex.: {32: "5 - Concordo totalmente"})
            - "texto": respostas dissertativas já juntas em uma string
        llm: cliente LangChain pronto (opcional). Se None e usar_llm_padrao,
            tenta criar o Groq a partir de GROQ_API_KEY.
        config: parâmetros de cálculo.

    Returns:
        dict com pontos_objetivos_brutos, penalizacoes, pontos_objetivos (após
        penalizações), scores (0-100 por área), area_principal, justificativa,
        fit_valores e origem ("llm" ou "local").
    """
    config = config or Config()
    respostas = candidato.get("respostas") or {}
    texto = str(candidato.get("texto") or "").strip()

    if llm is None and usar_llm_padrao:
        llm = criar_llm(config)

    objetivos = calcular_pontos_objetivos(respostas, config)
    areas = pontuar_areas(objetivos["finais"], texto, llm=llm, config=config)

    return {
        "pontos_objetivos_brutos": objetivos["brutos"],
        "penalizacoes": objetivos["penalizacoes"],
        "pontos_objetivos": objetivos["finais"],
        "scores": {a: round(areas["scores"][a], 1) for a in AREAS},
        "area_principal": areas["area_principal"],
        "justificativa": areas["justificativa"],
        "fit_valores": calcular_fit_valores(respostas, config),
        "origem": areas["origem"],
    }


def score_batch(
    candidatos: list[dict],
    llm: Any = None,
    config: Optional[Config] = None,
    pausa: float = 0.0,
    on_error: Optional[Callable[[int, Exception], None]] = None,
    usar_llm_padrao: bool = True,
) -> list[dict]:
    """Avalia vários candidatos (equivalente ao loop do notebook).

    Em erro, devolve scores zerados com area_principal="Erro".
    """
    import time

    config = config or Config()
    if llm is None and usar_llm_padrao:
        llm = criar_llm(config)

    resultados = []
    for i, cand in enumerate(candidatos):
        try:
            resultados.append(score_candidate(cand, llm=llm, config=config, usar_llm_padrao=False))
        except Exception as erro:
            if on_error:
                on_error(i, erro)
            zeros = {a: 0 for a in AREAS}
            resultados.append({
                "pontos_objetivos_brutos": dict(zeros), "penalizacoes": [],
                "pontos_objetivos": dict(zeros), "scores": dict(zeros),
                "area_principal": "Erro", "justificativa": "Erro",
                "fit_valores": {"pontos": 0, "maximo": 50, "minimo": config.fit_minimo,
                                "fit": "Não", "aprovado": False},
                "origem": "erro",
            })
        if pausa:
            time.sleep(pausa)
    return resultados


# --------------------------------------------------------------------------- #
# Leitura da planilha com pandas
# --------------------------------------------------------------------------- #

def url_exportacao_csv(url: str) -> str:
    """Converte um link do Google Sheets no link de exportação CSV.

    Mantém a aba (gid) do link, se houver. Links que não são do Sheets voltam iguais.
    """
    achado = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", url)
    if not achado:
        return url
    link = f"https://docs.google.com/spreadsheets/d/{achado.group(1)}/export?format=csv"
    gid = re.search(r"[#&?]gid=(\d+)", url)
    return link + (f"&gid={gid.group(1)}" if gid else "")


def ler_planilha(origem: Any):
    """Lê a planilha com pandas e devolve um DataFrame.

    `origem` pode ser: link do Google Sheets (a planilha precisa estar com acesso
    "qualquer pessoa com o link"), caminho de .csv, caminho de .xlsx/.xls ou um
    DataFrame (devolvido como está).
    """
    import pandas as pd

    if isinstance(origem, pd.DataFrame):
        return origem
    origem = str(origem)
    if origem.startswith(("http://", "https://")):
        return pd.read_csv(url_exportacao_csv(origem))
    if origem.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(origem)
    return pd.read_csv(origem)


def avaliar_dataframe(
    df: Any,
    llm: Any = None,
    config: Optional[Config] = None,
    pausa: float = 0.0,
    colunas_texto: Optional[Sequence[int]] = None,
    preprocessar: bool = True,
    usar_llm_padrao: bool = True,
):
    """Avalia todas as linhas de um DataFrame e devolve uma cópia com as colunas novas.

    Colunas adicionadas (mesmos nomes do notebook): Pontos_RH_Obj, Pontos_Proj_Obj,
    Pontos_Mkt_Obj, Pontos_Train_Obj (já com penalizações), Score_RH, Score_Projetos,
    Score_Marketing, Score_Training, Area_Sugerida, Analise_IA, Penalizacoes,
    Score_Valores_Liga e Fit_Valores ("Sim"/"Não").
    """
    config = config or Config()
    candidatos = [
        candidato_de_linha(list(linha), colunas_texto=colunas_texto, preprocessar=preprocessar)
        for linha in df.itertuples(index=False, name=None)
    ]
    resultados = score_batch(
        candidatos, llm=llm, config=config, pausa=pausa, usar_llm_padrao=usar_llm_padrao
    )

    saida = df.copy()
    saida["Pontos_RH_Obj"] = [r["pontos_objetivos"]["rh"] for r in resultados]
    saida["Pontos_Proj_Obj"] = [r["pontos_objetivos"]["projetos"] for r in resultados]
    saida["Pontos_Mkt_Obj"] = [r["pontos_objetivos"]["marketing"] for r in resultados]
    saida["Pontos_Train_Obj"] = [r["pontos_objetivos"]["training"] for r in resultados]
    saida["Score_RH"] = [r["scores"]["rh"] for r in resultados]
    saida["Score_Projetos"] = [r["scores"]["projetos"] for r in resultados]
    saida["Score_Marketing"] = [r["scores"]["marketing"] for r in resultados]
    saida["Score_Training"] = [r["scores"]["training"] for r in resultados]
    saida["Area_Sugerida"] = [r["area_principal"] for r in resultados]
    saida["Analise_IA"] = [r["justificativa"] for r in resultados]
    saida["Penalizacoes"] = [
        "; ".join(f"{p['area']} (col {p['coluna']}): {p['pontos']:g}" for p in r["penalizacoes"])
        for r in resultados
    ]
    saida["Score_Valores_Liga"] = [r["fit_valores"]["pontos"] for r in resultados]
    saida["Fit_Valores"] = [r["fit_valores"]["fit"] for r in resultados]
    return saida


def avaliar_planilha(origem: Any, **kwargs):
    """Lê a planilha (link, .csv, .xlsx ou DataFrame) e avalia todos os candidatos.

    Aceita os mesmos argumentos de `avaliar_dataframe` (llm, config, pausa,
    colunas_texto, preprocessar, usar_llm_padrao).
    """
    return avaliar_dataframe(ler_planilha(origem), **kwargs)


def _demo() -> None:
    respostas = {c: "4 - Concordo" for cols in COLUNAS_AREAS.values() for c in cols}
    respostas.update({c: "5 - Concordo totalmente" for c in COLUNAS_VALORES})
    respostas[43] = "2 - Discordo"   # penaliza Projetos
    respostas[38] = "1 - Discordo totalmente"  # penaliza Marketing (-2)
    exemplo = {
        "respostas": respostas,
        "texto": (
            "Gosto de trabalhar em equipe, mediar conflitos e dar feedback. "
            "Já ajudei colegas a aprender estatística com mentoria e material didático."
        ),
    }
    print(json.dumps(score_candidate(exemplo, usar_llm_padrao=False), ensure_ascii=False, indent=2))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Linha de comando:  python score.py <link|arquivo> [-o resultado.csv] [--sem-llm]"""
    import argparse

    ap = argparse.ArgumentParser(description="Avalia candidatos a partir de uma planilha.")
    ap.add_argument("origem", nargs="?", help="link do Google Sheets, .csv ou .xlsx")
    ap.add_argument("-o", "--saida", default="resultado.csv", help="CSV de saída")
    ap.add_argument("--sem-llm", action="store_true", help="usa só o avaliador local")
    ap.add_argument("--pausa", type=float, default=0.5, help="segundos entre chamadas à LLM")
    args = ap.parse_args(argv)

    if not args.origem:
        _demo()
        return 0

    resultado = avaliar_planilha(
        args.origem, pausa=0 if args.sem_llm else args.pausa, usar_llm_padrao=not args.sem_llm
    )
    resultado.to_csv(args.saida, index=False, encoding="utf-8-sig")
    print(f"{len(resultado)} candidatos avaliados -> {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
