import re
from datetime import datetime
import streamlit as st

from core.dados import ler_inscricoes, salvar_inscricao
from score import calcular_score

from core.perguntas import (
    PERGUNTAS_AFINIDADE,
    PERGUNTAS_DISSERTATIVAS,
    PERGUNTAS_VALORES,
    montar_respostas_score,
)

TODAS_AS_ESCALAS = {**PERGUNTAS_VALORES, **PERGUNTAS_AFINIDADE}


def email_valido(email: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email.strip()))


def email_ja_inscrito(email: str) -> bool:
    """True se o e-mail já existe na planilha (sem diferenciar maiúsculas/minúsculas)."""
    ler_inscricoes.clear()  # lê a planilha atualizada, não o cache de 30 s
    df = ler_inscricoes()
    if df.empty or "email" not in df.columns:
        return False
    emails = df["email"].astype(str).str.strip().str.lower()
    return email.strip().lower() in set(emails)


def resetar_inscricao() -> None:
    st.session_state["inscricao_concluida"] = False
    st.session_state["dados_confirmacao"] = {}
    for chave in list(TODAS_AS_ESCALAS) + list(PERGUNTAS_DISSERTATIVAS):
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
st.write("Preencha todos os campos obrigatórios (marcados com *) para concluir sua inscrição.")

with st.form("form_processo_seletivo"):
    st.header("1. Dados Pessoais")
    nome = st.text_input("Nome completo *")
    email = st.text_input("E-mail *")
    curso = st.text_input("Curso *")
    ano_inicio = st.number_input(
        "Ano de início na graduação *",
        min_value=2015,
        max_value=2027,
        value=None,
        step=1,
        placeholder="Ex: 2024",
    )

    st.divider()

    st.header("2. Valores da Liga")
    st.caption("Responda de **1 (Discordo totalmente)** a **5 (Concordo totalmente)**. Não existe resposta certa.")

    numero = 1
    respostas_valores = {}
    for chave, (pergunta, _coluna) in PERGUNTAS_VALORES.items():
        respostas_valores[chave] = st.radio(
            f"{numero}. {pergunta} *",
            options=[1, 2, 3, 4, 5],
            index=None,
            horizontal=True,
            key=chave,
        )
        numero += 1

    st.divider()

    st.header("3. Afinidade com as Áreas")
    st.caption("Mesma escala: de **1 (Discordo totalmente)** a **5 (Concordo totalmente)**.")

    respostas_afinidade = {}
    for chave, (pergunta, _coluna) in PERGUNTAS_AFINIDADE.items():
        respostas_afinidade[chave] = st.radio(
            f"{numero}. {pergunta} *",
            options=[1, 2, 3, 4, 5],
            index=None,
            horizontal=True,
            key=chave,
        )
        numero += 1

    st.divider()

    st.header("4. Perguntas Dissertativas")
    respostas_diss = {}
    for chave, pergunta in PERGUNTAS_DISSERTATIVAS.items():
        respostas_diss[chave] = st.text_area(
            f"{numero}. {pergunta} *",
            height=110,
            key=chave,
        )
        numero += 1

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

    respostas_escala = {**respostas_valores, **respostas_afinidade}
    escala_faltando = [
        idx for idx, chave in enumerate(TODAS_AS_ESCALAS, start=1)
        if respostas_escala[chave] is None
    ]
    if escala_faltando:
        erros.append(
            f"Responda às questões de múltipla escolha obrigatórias: **{', '.join(map(str, escala_faltando))}**."
        )

    inicio_diss = len(TODAS_AS_ESCALAS) + 1
    diss_faltando = [
        idx for idx, chave in enumerate(PERGUNTAS_DISSERTATIVAS, start=inicio_diss)
        if not respostas_diss[chave].strip()
    ]
    if diss_faltando:
        erros.append(f"Responda às questões dissertativas obrigatórias: **{', '.join(map(str, diss_faltando))}**.")

    if erros:
        for erro in erros:
            st.error(erro)
    else:
        # Bloqueia e-mail que já se inscreveu
        try:
            with st.spinner("Verificando inscrição..."):
                duplicado = email_ja_inscrito(email)
        except Exception as erro:
            st.error(f"Erro ao verificar a planilha: {erro}")
            st.stop()

        if duplicado:
            st.error(
                "Já existe uma inscrição com este e-mail. Cada pessoa pode se inscrever "
                "apenas uma vez. Se acha que é um engano, fale com a gente:  psdatascience84@gmail.com"
            )
            st.stop()

        # Pontuação objetiva, penalizações e fit de valores via score.py
        resultado_score = calcular_score(montar_respostas_score(respostas_escala))

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
            **respostas_valores,
            **respostas_afinidade,
            **{k: v.strip() for k, v in respostas_diss.items()},
            "Pontos_RH": resultado_score["pontos"]["rh"],
            "Pontos_Projetos": resultado_score["pontos"]["projetos"],
            "Pontos_Training": resultado_score["pontos"]["training"],
            "Pontos_Marketing": resultado_score["pontos"]["marketing"],
            "Area_Sugerida": resultado_score["area_sugerida"] or "Indefinida",
            "Penalizacoes": penalizacoes_fmt,
            "Fit_Valores": "Sim" if resultado_score["fit"] else "Não",
            "Fit_Pontos": resultado_score["fit_pontos"],
        }

        try:
            with st.spinner("Salvando inscrição..."):
                salvar_inscricao(registro)
            st.session_state["dados_confirmacao"] = registro
            st.session_state["inscricao_concluida"] = True
            st.rerun()
        except Exception as erro:
            st.error(f"Erro ao salvar inscrição na planilha: {erro