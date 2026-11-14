import re
from datetime import datetime
import streamlit as st

from core.dados import salvar_inscricao
from score import calcular_score

PERGUNTAS_OBJETIVAS = {
    "obj_1": "Gosto de ouvir pessoas, mediar conflitos e cuidar do clima de uma equipe.",
    "obj_2": "Tenho facilidade para organizar cronogramas, cobrar prazos e acompanhar metas.",
    "obj_3": "Gosto de estudar assuntos técnicos a fundo para ensinar e capacitar outras pessoas.",
    "obj_4": "Tenho interesse em criação de conteúdo, identidade visual e estratégias de divulgação.",
    "obj_5": "Prefiro resolver problemas práticos com entregas bem definidas e contato com clientes/parceiros.",
    "obj_6": "Sinto-me motivado(a) planejando dinâmicas de integração, recrutamento e cultura.",
    "obj_7": "Tenho facilidade para estruturar trilhas de aprendizado ou comunicar ideias de forma criativa.",
}

PERGUNTAS_DISSERTATIVAS = {
    "diss_1": "Em um trabalho em grupo com prazo apertado e equipe desmotivada, qual papel você costuma assumir naturalmente?",
    "diss_2": "Qual das quatro áreas (RH, Projetos, Training ou Marketing) mais chama sua atenção hoje e por quê?",
    "diss_3": "Conte uma experiência em que você teve iniciativa para resolver um problema ou melhorar algum processo.",
}

# Liga cada pergunta do formulário aos índices de coluna configurados em score.py (COLUNAS_AREAS)
MAPA_FORM_PARA_SCORE = {
    "obj_1": [32],      # RH
    "obj_6": [37],      # RH
    "obj_2": [33],      # Projetos
    "obj_5": [35],      # Projetos
    "obj_3": [36],      # Training
    "obj_4": [34],      # Marketing
    "obj_7": [40, 31],  # Training / Marketing
}


def email_valido(email: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email.strip()))


def montar_respostas_score(respostas_obj: dict[str, int]) -> dict[int, int]:
    """Converte as respostas do formulário para o dicionário {coluna: nota} de calcular_score."""
    respostas_mapeadas: dict[int, int] = {}
    for chave, colunas in MAPA_FORM_PARA_SCORE.items():
        for col in colunas:
            respostas_mapeadas[col] = respostas_obj[chave]
    return respostas_mapeadas


def resetar_inscricao() -> None:
    st.session_state["inscricao_concluida"] = False
    st.session_state["dados_confirmacao"] = {}
    for chave in list(PERGUNTAS_OBJETIVAS.keys()) + list(PERGUNTAS_DISSERTATIVAS.keys()):
        st.session_state.pop(chave, None)


def exibir_tela_confirmacao(dados: dict) -> None:
    st.title("Inscrição Confirmada!")
    st.success(
        f"Obrigado, **{dados['nome']}**! Suas respostas foram registradas com sucesso no processo seletivo."
    )

    with st.container(border=True):
        st.subheader("Comprovante de Inscrição")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Nome:** {dados['nome']}")
            st.write(f"**E-mail:** {dados['email']}")
        with col2:
            st.write(f"**Curso:** {dados['curso']}")
            st.write(f"**Ano de início:** {dados['ano_inicio']}")

        st.caption(f"Registrado em: {dados['data_inscricao']}")

    st.info(
        "Fique atento(a) ao e-mail cadastrado — enviaremos por lá as informações sobre as próximas etapas."
    )

    st.button("Fazer nova inscrição", on_click=resetar_inscricao, type="secondary")


# --- CONTROLE DE ESTADO ---
if "inscricao_concluida" not in st.session_state:
    st.session_state["inscricao_concluida"] = False
if "dados_confirmacao" not in st.session_state:
    st.session_state["dados_confirmacao"] = {}

if st.session_state["inscricao_concluida"]:
    exibir_tela_confirmacao(st.session_state["dados_confirmacao"])
    st.stop()

# --- FORMULÁRIO ---
st.title("Formulário de Inscrição — Processo Seletivo")
st.write("Preencha todos os campos obrigatórios (**\***) para concluir sua inscrição.")

with st.form("form_processo_seletivo"):
    st.header("1. Dados Pessoais")
    nome = st.text_input("Nome completo *")
    email = st.text_input("E-mail *")
    curso = st.text_input("Curso *")
    ano_inicio = st.number_input(
        "Ano de início na graduação *",
        min_value=2015,
        max_value=2026,
        value=None,
        step=1,
        placeholder="Ex: 2024",
    )

    st.divider()

    st.header("2. Questionário de Afinidade e Cultura")
    st.caption("Nas questões de 1 a 7, responda de **1 (Discordo totalmente)** a **5 (Concordo totalmente)**.")

    respostas_obj = {}
    for idx, (chave, pergunta) in enumerate(PERGUNTAS_OBJETIVAS.items(), start=1):
        respostas_obj[chave] = st.radio(
            f"{idx}. {pergunta} *",
            options=[1, 2, 3, 4, 5],
            index=None,
            horizontal=True,
            key=chave,
        )

    st.divider()

    respostas_diss = {}
    for idx, (chave, pergunta) in enumerate(PERGUNTAS_DISSERTATIVAS.items(), start=8):
        respostas_diss[chave] = st.text_area(
            f"{idx}. {pergunta} *",
            height=110,
            key=chave,
        )

    enviado = st.form_submit_button("Enviar Inscrição", type="primary")

if enviado:
    erros = []

    if not nome.strip():
        erros.append("O campo **Nome completo** é obrigatório.")
    if not email.strip():
        erros.append("O campo **E-mail** é obrigatório.")
    elif not email_valido(email):
        erros.append("O **E-mail** informado não é válido.")
    if not curso.strip():
        erros.append("O campo **Curso** é obrigatório.")
    if ano_inicio is None:
        erros.append("O campo **Ano de início** é obrigatório.")

    obj_faltando = [
        idx for idx, chave in enumerate(PERGUNTAS_OBJETIVAS, start=1)
        if respostas_obj[chave] is None
    ]
    if obj_faltando:
        erros.append(f"Responda às questões objetivas obrigatórias: **{', '.join(map(str, obj_faltando))}**.")

    diss_faltando = [
        idx for idx, chave in enumerate(PERGUNTAS_DISSERTATIVAS, start=8)
        if not respostas_diss[chave].strip()
    ]
    if diss_faltando:
        erros.append(f"Responda às questões dissertativas obrigatórias: **{', '.join(map(str, diss_faltando))}**.")

    if erros:
        for erro in erros:
            st.error(erro)
    else:
        # Calcula pontuação objetiva e penalizações via score.py
        respostas_score = montar_respostas_score(respostas_obj)
        resultado_score = calcular_score(respostas_score)

        penalizacoes_fmt = "; ".join(
            f"{p['area']} (col {p['coluna']}): {p['pontos']:g}"
            for p in resultado_score["penalizacoes"]
        )

        registro = {
            "data_inscricao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "nome": nome.strip(),
            "email": email.strip().lower(),
            "curso": curso.strip(),
            "ano_inicio": int(ano_inicio),
            **respostas_obj,
            **{k: v.strip() for k, v in respostas_diss.items()},
            "Pontos_RH": resultado_score["pontos"]["rh"],
            "Pontos_Projetos": resultado_score["pontos"]["projetos"],
            "Pontos_Training": resultado_score["pontos"]["training"],
            "Pontos_Marketing": resultado_score["pontos"]["marketing"],
            "Area_Sugerida": resultado_score["area_sugerida"] or "Indefinida",
            "Penalizacoes": penalizacoes_fmt,
        }

        try:
            with st.spinner("Salvando inscrição..."):
                salvar_inscricao(registro)
            st.session_state["dados_confirmacao"] = registro
            st.session_state["inscricao_concluida"] = True
            st.rerun()
        except Exception as erro:
            st.error(f"Erro ao salvar inscrição na planilha: {erro}")