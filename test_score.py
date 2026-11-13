"""Testes do score.py. Rodar com:  pytest -v"""

import json

import pytest

import score
from score import (
    COLUNAS_AREAS,
    COLUNAS_VALORES,
    Config,
    calcular_fit_valores,
    calcular_pontos_objetivos,
    candidato_de_linha,
    extrair_json,
    extrair_nota,
    preprocessar_texto,
    score_batch,
    score_candidate,
)


# --------------------------------------------------------------------------- #
# Fixtures e dublês
# --------------------------------------------------------------------------- #

@pytest.fixture
def respostas_base():
    """Todas as perguntas de área = 3 (9 pts por área) e valores = 5 (fit 50)."""
    r = {c: "3 - Neutro" for cols in COLUNAS_AREAS.values() for c in cols}
    r.update({c: "5 - Concordo totalmente" for c in COLUNAS_VALORES})
    return r


class RespostaFalsa:
    def __init__(self, content):
        self.content = content


class LLMFalsa:
    """Imita o cliente LangChain: tem .invoke() e devolve algo com .content."""

    def __init__(self, content):
        self.content = content
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return RespostaFalsa(self.content)


class LLMQuebrada:
    def invoke(self, prompt):
        raise RuntimeError("rate limit")


# --------------------------------------------------------------------------- #
# extrair_nota
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("5 - Concordo totalmente", 5),
        ("1", 1),
        (4, 4),
        (None, 0),
        (float("nan"), 0),
        ("sem número", 0),
        ("", 0),
    ],
)
def test_extrair_nota(entrada, esperado):
    assert extrair_nota(entrada) == esperado


# --------------------------------------------------------------------------- #
# Pontos objetivos e penalizações
# --------------------------------------------------------------------------- #

def test_pontos_sem_penalizacao(respostas_base):
    r = calcular_pontos_objetivos(respostas_base)
    assert r["brutos"] == {"rh": 9, "projetos": 9, "marketing": 9, "training": 9}
    assert r["finais"] == r["brutos"]
    assert r["penalizacoes"] == []


def test_penalizacao_simples(respostas_base):
    respostas_base[32] = "1 - Discordo totalmente"  # RH: ruim = 1
    r = calcular_pontos_objetivos(respostas_base)
    assert r["brutos"]["rh"] == 7          # 1 + 3 + 3
    assert r["finais"]["rh"] == 5          # -2
    assert len(r["penalizacoes"]) == 1
    assert r["penalizacoes"][0]["area"] == "RH"
    assert r["penalizacoes"][0]["coluna"] == 32


def test_penalizacao_aceita_chave_str(respostas_base):
    respostas_base[32] = "1"
    como_str = {str(k): v for k, v in respostas_base.items()}
    assert calcular_pontos_objetivos(como_str)["finais"]["rh"] == 5


def test_penalizacao_com_duas_respostas_ruins(respostas_base):
    respostas_base[43] = "2 - Discordo"  # Projetos: ruins = [1, 2]
    r = calcular_pontos_objetivos(respostas_base)
    assert r["finais"]["projetos"] == 9 - 1 - 2  # 3->2 na soma, depois -2


def test_resposta_nao_penalizada_fora_da_lista(respostas_base):
    respostas_base[40] = "1 - Discordo totalmente"  # Training só penaliza 2
    r = calcular_pontos_objetivos(respostas_base)
    assert r["penalizacoes"] == []


def test_nota_nunca_fica_negativa(respostas_base):
    for c in (32, 37, 39):
        respostas_base[c] = "1"
    r = calcular_pontos_objetivos(respostas_base)
    assert r["brutos"]["rh"] == 3
    assert r["finais"]["rh"] == 0
    assert all(v >= 0 for v in r["finais"].values())


def test_penalidade_configuravel(respostas_base):
    respostas_base[32] = "1"
    r = calcular_pontos_objetivos(respostas_base, Config(penalidade=3))
    assert r["finais"]["rh"] == 4


def test_respostas_vazias_dao_zero():
    r = calcular_pontos_objetivos({})
    assert r["finais"] == {"rh": 0, "projetos": 0, "marketing": 0, "training": 0}


# --------------------------------------------------------------------------- #
# Fit de valores
# --------------------------------------------------------------------------- #

def test_fit_maximo(respostas_base):
    fit = calcular_fit_valores(respostas_base)
    assert fit["pontos"] == 50
    assert fit["fit"] == "Sim"
    assert fit["aprovado"] is True


def test_fit_no_limite_30_aprova():
    respostas = {c: "3" for c in COLUNAS_VALORES}  # 30
    assert calcular_fit_valores(respostas)["fit"] == "Sim"


def test_fit_abaixo_do_limite_reprova():
    respostas = {c: "3" for c in COLUNAS_VALORES}
    respostas[COLUNAS_VALORES[0]] = "2"  # 29
    fit = calcular_fit_valores(respostas)
    assert fit["pontos"] == 29
    assert fit["fit"] == "Não"
    assert fit["aprovado"] is False


# --------------------------------------------------------------------------- #
# LLM (sempre com dublê: nunca chama a API de verdade)
# --------------------------------------------------------------------------- #

def test_extrair_json_com_cerca_markdown():
    bruto = '```json\n{"score_rh": 80}\n```'
    assert extrair_json(bruto) == {"score_rh": 80}


def test_extrair_json_com_texto_em_volta():
    assert extrair_json('Claro! {"a": 1} Espero ter ajudado.') == {"a": 1}


def test_score_candidate_com_llm_falsa(respostas_base):
    llm = LLMFalsa(json.dumps({
        "score_rh": 90, "score_projetos": 40, "score_marketing": 150,
        "score_training": 20, "area_principal": "RH", "justificativa": "ok",
    }))
    r = score_candidate({"respostas": respostas_base, "texto": "texto"}, llm=llm)
    assert r["origem"] == "llm"
    assert r["scores"]["rh"] == 90
    assert r["scores"]["marketing"] == 100  # limitado a 100
    assert r["area_principal"] == "RH"
    # o prompt recebeu os pontos objetivos já penalizados
    assert "RH: 9/15" in llm.prompts[0]


def test_llm_recebe_pontos_apos_penalizacao(respostas_base):
    respostas_base[32] = "1"
    llm = LLMFalsa('{"score_rh": 1}')
    score_candidate({"respostas": respostas_base, "texto": ""}, llm=llm)
    assert "RH: 5/15" in llm.prompts[0]


def test_llm_quebrada_cai_no_avaliador_local(respostas_base):
    r = score_candidate({"respostas": respostas_base, "texto": "equipe"}, llm=LLMQuebrada())
    assert r["origem"] == "local"
    assert "LLM falhou" in r["justificativa"]


def test_llm_com_json_invalido_cai_no_local(respostas_base):
    r = score_candidate({"respostas": respostas_base, "texto": ""}, llm=LLMFalsa("não é json"))
    assert r["origem"] == "local"


# --------------------------------------------------------------------------- #
# Avaliador local
# --------------------------------------------------------------------------- #

def test_local_sem_texto_usa_so_objetivo(respostas_base):
    r = score_candidate({"respostas": respostas_base, "texto": ""}, usar_llm_padrao=False)
    # 9/15 = 60% do objetivo, pesado em 50% -> 30
    assert r["scores"]["rh"] == pytest.approx(30.0)


def test_local_palavras_chave_sobem_a_area(respostas_base):
    texto = "ensinar mentoria paciencia ajudar"
    r = score_candidate({"respostas": respostas_base, "texto": texto}, usar_llm_padrao=False)
    assert r["scores"]["training"] > r["scores"]["rh"]
    assert r["area_principal"] == "Training"


def test_scores_sempre_entre_0_e_100(respostas_base):
    r = score_candidate({"respostas": respostas_base, "texto": "x " * 500}, usar_llm_padrao=False)
    assert all(0 <= v <= 100 for v in r["scores"].values())


# --------------------------------------------------------------------------- #
# Linha da planilha e pré-processamento
# --------------------------------------------------------------------------- #

def test_candidato_de_linha_monta_respostas_e_texto():
    linha = [None] * 50
    linha[32] = "5 - Concordo"
    linha[6] = "Eu GOSTO de Ensinar!"
    c = candidato_de_linha(linha, preprocessar=False)
    assert c["respostas"][32] == "5 - Concordo"
    assert c["texto"] == "Eu GOSTO de Ensinar!"


def test_candidato_de_linha_ignora_texto_vazio_e_indice_fora():
    linha = [None] * 10
    linha[6] = float("nan")
    linha[7] = "ok"
    c = candidato_de_linha(linha, preprocessar=False)  # colunas 27+ não existem
    assert c["texto"] == "ok"


def test_preprocessar_sem_spacy_remove_acento_e_pontuacao(monkeypatch):
    monkeypatch.setattr(score, "_carregar_spacy", lambda: None)
    assert preprocessar_texto("É ÓTIMO, Ensinar!!") == "e otimo ensinar"
    assert preprocessar_texto(None) == ""


# --------------------------------------------------------------------------- #
# Lote
# --------------------------------------------------------------------------- #

def test_score_batch_isola_erro(respostas_base):
    ok = {"respostas": respostas_base, "texto": "equipe"}
    ruim = {"respostas": 123}  # vai estourar dentro de score_candidate
    erros = []
    res = score_batch([ok, ruim, ok], llm=LLMFalsa("{}"), on_error=lambda i, e: erros.append(i))
    assert [r["area_principal"] == "Erro" for r in res] == [False, True, False]
    assert erros == [1]


# --------------------------------------------------------------------------- #
# Planilha com pandas
# --------------------------------------------------------------------------- #

def test_url_exportacao_csv_mantem_gid():
    url = ("https://docs.google.com/spreadsheets/d/1xytU497CeHlK23ZKKJLBy7a23-mA2qDwQhFCVEOZnmI"
           "/edit?resourcekey=&gid=1513164428#gid=1513164428")
    assert score.url_exportacao_csv(url) == (
        "https://docs.google.com/spreadsheets/d/1xytU497CeHlK23ZKKJLBy7a23-mA2qDwQhFCVEOZnmI"
        "/export?format=csv&gid=1513164428"
    )


def test_url_exportacao_csv_sem_gid_e_link_nao_sheets():
    assert score.url_exportacao_csv("https://docs.google.com/spreadsheets/d/ABC123/edit").endswith(
        "/d/ABC123/export?format=csv"
    )
    assert score.url_exportacao_csv("https://exemplo.com/dados.csv") == "https://exemplo.com/dados.csv"


def _df_exemplo(respostas_base):
    pd = pytest.importorskip("pandas")
    linha = [None] * 50
    for coluna, valor in respostas_base.items():
        linha[coluna] = valor
    linha[6] = "Gosto de ensinar e de mentoria"
    return pd.DataFrame([linha, linha])


def test_avaliar_dataframe_adiciona_colunas(respostas_base):
    df = _df_exemplo(respostas_base)
    out = score.avaliar_dataframe(df, usar_llm_padrao=False)
    for col in ["Pontos_RH_Obj", "Score_RH", "Score_Training", "Area_Sugerida",
                "Analise_IA", "Penalizacoes", "Score_Valores_Liga", "Fit_Valores"]:
        assert col in out.columns
    assert len(out) == 2
    assert (out["Fit_Valores"] == "Sim").all()
    assert list(df.columns) == list(range(50))  # original não foi alterado


def test_ler_planilha_csv_e_avaliar(tmp_path, respostas_base):
    df = _df_exemplo(respostas_base)
    caminho = tmp_path / "respostas.csv"
    df.to_csv(caminho, index=False)
    out = score.avaliar_planilha(str(caminho), usar_llm_padrao=False)
    assert len(out) == 2
    assert out["Score_Valores_Liga"].iloc[0] == 50


def test_ler_planilha_aceita_dataframe(respostas_base):
    df = _df_exemplo(respostas_base)
    assert score.ler_planilha(df) is df


# --------------------------------------------------------------------------- #
# pontos_area, penalizar, fit_valores e calcular_score
# --------------------------------------------------------------------------- #

from score import REGRAS_POR_AREA, calcular_score, fit_valores, penalizar, pontos_area


@pytest.fixture
def candidata_marina():
    """Candidata inventada: Training lidera nos pontos brutos (12), mas respondeu
    "2 - Discordo" na coluna 40 (penalizada em Training), então Projetos passa à frente.

    brutos:  RH 9 | Projetos 11 | Marketing 9 | Training 12
    finais:  RH 9 | Projetos 11 | Marketing 9 | Training 10
    valores: 10 perguntas x 4 = 40 (fit)
    """
    respostas = {
        32: "3 - Neutro", 37: "3 - Neutro", 39: "3 - Neutro",                       # RH = 9
        33: "4 - Concordo", 35: "4 - Concordo", 43: "3 - Neutro",                   # Projetos = 11
        31: "3 - Neutro", 34: "3 - Neutro", 38: "3 - Neutro",                       # Marketing = 9
        36: "5 - Concordo totalmente", 40: "2 - Discordo", 42: "5 - Concordo totalmente",  # Training = 12
    }
    respostas.update({c: "4 - Concordo" for c in COLUNAS_VALORES})
    return respostas


def test_pontos_area_soma_as_perguntas(respostas_base):
    assert pontos_area(respostas_base, COLUNAS_AREAS["rh"]) == 9
    assert pontos_area({32: "5 - Concordo", 37: "4", 39: "2"}, [32, 37, 39]) == 11


def test_pontos_area_resposta_ausente_ou_sem_numero_vale_zero():
    respostas = {32: "5", 37: None, 39: "sem número"}
    assert pontos_area(respostas, [32, 37, 39]) == 5
    assert pontos_area({}, [32, 37, 39]) == 0
    assert pontos_area({32: "5"}, []) == 0


def test_pontos_area_aceita_chaves_texto():
    assert pontos_area({"32": "5", "37": "4"}, [32, 37]) == 9


def test_penalizar_desconta_por_resposta_ruim():
    respostas = {43: "2 - Discordo"}
    assert penalizar(10, respostas, [(43, [1, 2])]) == 8
    assert penalizar(10, respostas, [(43, [1, 2])], penalidade=3) == 7


def test_penalizar_ignora_resposta_fora_da_lista():
    assert penalizar(10, {43: "3 - Neutro"}, [(43, [1, 2])]) == 10
    assert penalizar(10, {}, [(43, [1, 2])]) == 10  # sem resposta não penaliza


def test_penalizar_nunca_fica_negativo():
    respostas = {32: "1", 37: "1", 39: "1"}
    assert penalizar(1, respostas, REGRAS_POR_AREA["rh"]) == 0


def test_fit_valores_limite_30():
    assert fit_valores({c: "3" for c in COLUNAS_VALORES}) is True        # 30
    abaixo = {c: "3" for c in COLUNAS_VALORES}
    abaixo[COLUNAS_VALORES[0]] = "2"                                    # 29
    assert fit_valores(abaixo) is False
    assert fit_valores({}) is False


def test_calcular_score_candidata_com_resposta_penalizada(candidata_marina):
    r = calcular_score(candidata_marina)

    assert r["pontos_brutos"] == {"rh": 9, "projetos": 11, "marketing": 9, "training": 12}
    assert r["pontos"] == {"rh": 9, "projetos": 11, "marketing": 9, "training": 10}
    assert r["penalizacoes"] == [
        {"area": "Training", "coluna": 40, "resposta": "2 - Discordo", "pontos": -2}
    ]
    # sem a penalização, Training (12) seria a sugerida; com ela, vence Projetos (11)
    assert r["area_sugerida"] == "Projetos"
    assert r["areas_empatadas"] == ["Projetos"]
    assert r["fit"] is True
    assert r["fit_pontos"] == 40


def test_calcular_score_sem_penalizacao_sugere_a_area_de_maior_nota(respostas_base):
    respostas_base[36] = "5"
    respostas_base[40] = "5"
    respostas_base[42] = "5"
    r = calcular_score(respostas_base)
    assert r["pontos"]["training"] == 15
    assert r["penalizacoes"] == []
    assert r["area_sugerida"] == "Training"


def test_calcular_score_empate_usa_a_primeira_area_e_lista_as_empatadas(respostas_base):
    r = calcular_score(respostas_base)  # todas as áreas com 9
    assert r["areas_empatadas"] == ["RH", "Projetos", "Marketing", "Training"]
    assert r["area_sugerida"] == "RH"


def test_calcular_score_sem_respostas():
    r = calcular_score({})
    assert r["pontos"] == {"rh": 0, "projetos": 0, "marketing": 0, "training": 0}
    assert r["area_sugerida"] is None
    assert r["areas_empatadas"] == []
    assert r["fit"] is False
    assert r["fit_pontos"] == 0


def test_calcular_score_respeita_config(candidata_marina):
    r = calcular_score(candidata_marina, Config(penalidade=5, fit_minimo=45))
    assert r["pontos"]["training"] == 7   # 12 - 5
    assert r["fit"] is False              # 40 < 45


def test_calcular_score_concorda_com_score_candidate(candidata_marina):
    simples = calcular_score(candidata_marina)
    completo = score_candidate({"respostas": candidata_marina, "texto": ""}, usar_llm_padrao=False)
    assert simples["pontos"] == completo["pontos_objetivos"]
    assert simples["penalizacoes"] == completo["penalizacoes"]
    assert simples["fit"] == completo["fit_valores"]["aprovado"]
