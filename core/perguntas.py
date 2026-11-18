"""core/perguntas.py - Perguntas do formulário e ligação com as colunas do score.

Cada pergunta é:  chave -> (texto, coluna_no_score.py)

ATENÇÃO: os textos abaixo são PROVISÓRIOS. Quando a Giovana entregar a lista
final, troque só os textos (mantenha as chaves e as colunas). As chaves viram os
nomes das colunas na planilha do Google Sheets.
"""

from __future__ import annotations

# 10 perguntas de valores da Liga (escala 1-5) -> somam o "fit de valores"
PERGUNTAS_VALORES = {
    "valores_1": ("Prefiro entregar algo bem feito no prazo do que perfeito depois do prazo.", 9),
    "valores_2": ("Gosto de aprender coisas novas mesmo quando não são obrigatórias.", 10),
    "valores_3": ("Quando alguém do grupo trava, eu paro o que estou fazendo para ajudar.", 11),
    "valores_4": ("Me sinto confortável em dar e receber feedback direto.", 13),
    "valores_5": ("Cumpro o que combino, mesmo quando ninguém está cobrando.", 14),
    "valores_6": ("Admito quando erro e busco corrigir sem esperar que alguém aponte.", 15),
    "valores_7": ("Prefiro trabalhar em equipe do que sozinho(a) quando o objetivo é grande.", 16),
    "valores_8": ("Consigo conciliar a Liga com a faculdade sem deixar compromissos para trás.", 18),
    "valores_9": ("Compartilho o que aprendo com os colegas, em vez de guardar só para mim.", 19),
    "valores_10": ("Aceito tarefas que não são as minhas favoritas quando a equipe precisa.", 20),
}

# 12 perguntas de afinidade (escala 1-5), 3 por área. A ordem está misturada
# de propósito, para não ficar óbvio qual área cada pergunta mede.
PERGUNTAS_AFINIDADE = {
    "rh_1": ("Gosto de ouvir pessoas, mediar conflitos e cuidar do clima de uma equipe.", 32),
    "projetos_1": ("Tenho facilidade para organizar cronogramas, cobrar prazos e acompanhar metas.", 33),
    "marketing_1": ("Tenho facilidade para comunicar ideias de forma criativa e atrativa.", 31),
    "training_1": ("Gosto de estudar assuntos técnicos a fundo para ensinar e capacitar outras pessoas.", 36),
    "rh_2": ("Sinto-me motivado(a) planejando dinâmicas de integração, recrutamento e cultura.", 37),
    "projetos_2": ("Prefiro resolver problemas práticos com entregas bem definidas e contato com clientes/parceiros.", 35),
    "marketing_2": ("Tenho interesse em criação de conteúdo, identidade visual e estratégias de divulgação.", 34),
    "training_2": ("Tenho facilidade para estruturar trilhas de aprendizado e materiais de estudo.", 40),
    "rh_3": ("Costumo perceber quando alguém da equipe não está bem e procuro ajudar.", 39),
    "projetos_3": ("Fico incomodado(a) quando um projeto não tem escopo, responsáveis e prazos definidos.", 43),
    "marketing_3": ("Gosto de acompanhar redes sociais e pensar em como divulgar um evento.", 38),
    "training_3": ("Me sinto à vontade para explicar um conteúdo difícil para outras pessoas.", 42),
}

PERGUNTAS_DISSERTATIVAS = {
    "diss_1": "Em um trabalho em grupo com prazo apertado e equipe desmotivada, qual papel você costuma assumir naturalmente?",
    "diss_2": "Qual das quatro áreas (RH, Projetos, Training ou Marketing) mais chama sua atenção hoje e por quê?",
    "diss_3": "Conte uma experiência em que você teve iniciativa para resolver um problema ou melhorar algum processo.",
}


def montar_respostas_score(respostas: dict) -> dict[int, object]:
    """Converte {chave_da_pergunta: nota} em {coluna_do_score: nota}.

    É o formato que `score.calcular_score` espera. Chave ausente vira None (nota 0).
    """
    todas = {**PERGUNTAS_VALORES, **PERGUNTAS_AFINIDADE}
    return {coluna: respostas.get(chave) for chave, (_, coluna) in todas.items()}


CABECALHO_PLANILHA = (
    ["data_inscricao", "nome", "email", "curso", "ano_inicio"]
    + list(PERGUNTAS_VALORES)
    + list(PERGUNTAS_AFINIDADE)
    + list(PERGUNTAS_DISSERTATIVAS)
    + [
        "Pontos_RH", "Pontos_Projetos", "Pontos_Training", "Pontos_Marketing",
        "Area_Sugerida", "Penalizacoes", "Fit_Valores", "Fit_Pontos",
    ]
)
