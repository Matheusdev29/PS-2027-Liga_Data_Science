import hmac
import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Processo Seletivo", layout="wide")

ARQUIVO_CSV_LOCAL = "inscricoes.csv"
AREAS = ["RH", "Projetos", "Training", "Marketing"]

# Mapeamento das questões objetivas por área (dissertativas são desconsideradas na pontuação)
MAPA_QUESTOES_AREA = {
    "RH": ["obj_1", "obj_6"],
    "Projetos": ["obj_2", "obj_5"],
    "Training": ["obj_3", "obj_7"],
    "Marketing": ["obj_4", "obj_7"],
}


def verificar_autenticacao() -> bool:
    """Controla o login usando a senha definida em .streamlit/secrets.toml."""
    if st.session_state.get("autenticado", False):
        return True

    st.title("Acesso Restrito — Painel do Processo Seletivo")

    try:
        senha_correta = str(st.secrets["painel_senha"])
    except Exception:
        st.error(
            "Arquivo `.streamlit/secrets.toml` não encontrado ou sem a chave `painel_senha` na raiz do projeto."
        )
        st.stop()

    with st.form("form_login"):
        senha_digitada = st.text_input("Digite a senha de acesso:", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")

    if entrar:
        if hmac.compare_digest(senha_digitada, senha_correta):
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")

    return False

def carregar_dados(arquivo_upload) -> pd.DataFrame | None:
    """Carrega o CSV enviado por upload ou, na ausência dele, o arquivo local."""
    if arquivo_upload is not None:
        return pd.read_csv(arquivo_upload)

    if os.path.exists(ARQUIVO_CSV_LOCAL):
        return pd.read_csv(ARQUIVO_CSV_LOCAL)

    return None


def calcular_pontuacao_objetiva(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula o score (0 a 100%) por área usando apenas as questões objetivas."""
    df_calc = df.copy()

    # Garante que as colunas objetivas sejam numéricas
    todas_obj = sorted({col for cols in MAPA_QUESTOES_AREA.values() for col in cols})
    for col in todas_obj:
        if col in df_calc.columns:
            df_calc[col] = pd.to_numeric(df_calc[col], errors="coerce").fillna(0)
        else:
            st.error(f"Coluna esperada não encontrada no CSV: `{col}`")
            st.stop()

    # Calcula a porcentagem de afinidade para cada área (escala de 1 a 5 por questão)
    colunas_score = []
    for area, questoes in MAPA_QUESTOES_AREA.items():
        pontuacao_maxima = len(questoes) * 5
        col_score = f"Score {area} (%)"
        df_calc[col_score] = ((df_calc[questoes].sum(axis=1) / pontuacao_maxima) * 100).round(1)
        colunas_score.append(col_score)

    # Identifica a área de maior pontuação objetiva de cada candidato
    df_calc["Área Principal (Objetiva)"] = (
        df_calc[colunas_score]
        .idxmax(axis=1)
        .str.replace("Score ", "", regex=False)
        .str.replace(" (%)", "", regex=False)
    )

    return df_calc


# --- BLOQUEIO POR SENHA ---
if not verificar_autenticacao():
    st.stop()

# --- BARRA LATERAL: FONTE DE DADOS, DOWNLOAD, FILTROS E LOGOUT ---
with st.sidebar:
    st.header("Configurações do Painel")

    arquivo_upload = st.file_uploader(
        "Carregar arquivo CSV (opcional)",
        type=["csv"],
        help="Se nenhum arquivo for enviado, o painel usará o arquivo local 'inscricoes.csv'.",
    )

    # Botão para baixar o CSV salvo localmente no servidor/máquina
    if os.path.exists(ARQUIVO_CSV_LOCAL):
        with open(ARQUIVO_CSV_LOCAL, "rb") as f:
            st.download_button(
                label="Baixar CSV local",
                data=f.read(),
                file_name=ARQUIVO_CSV_LOCAL,
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.caption("O arquivo `inscricoes.csv` ainda não foi gerado localmente.")

    st.divider()
    area_filtro = st.selectbox(
        "Filtrar por Área",
        options=["Todas"] + AREAS,
    )

    st.divider()
    if st.button("Sair do Painel", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()


# --- CORPO PRINCIPAL ---
st.title("Painel de Avaliação — Processo Seletivo")

df_raw = carregar_dados(arquivo_upload)

if df_raw is None or df_raw.empty:
    st.warning(
        "Nenhuma inscrição encontrada. Aguarde envios pelo formulário local ou faça o upload de um CSV na barra lateral."
    )
    st.stop()

fonte_atual = f"Upload: `{arquivo_upload.name}`" if arquivo_upload else f"Arquivo local: `{ARQUIVO_CSV_LOCAL}`"
st.caption(f"Fonte de dados ativa: {fonte_atual}")

df = calcular_pontuacao_objetiva(df_raw)

# Aplicação do filtro por área
if area_filtro != "Todas":
    df_exibido = df[df["Área Principal (Objetiva)"] == area_filtro].sort_values(
        by=f"Score {area_filtro} (%)", ascending=False
    )
else:
    df_exibido = df.copy()

# --- CONTADORES (KPIs) ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total de Candidaturas", len(df))
for idx, area in enumerate(AREAS, start=2):
    qtd_area = int((df["Área Principal (Objetiva)"] == area).sum())
    locals()[f"col{idx}"].metric(f"Afinidade: {area}", qtd_area)

st.divider()

# --- TABELA GERAL: DADOS PESSOAIS + PONTUAÇÕES ---
st.subheader(
    f"Candidatos ({len(df_exibido)} exibidos)"
    + (f" — Filtro: {area_filtro}" if area_filtro != "Todas" else "")
)

colunas_tabela = [
    "nome",
    "email",
    "curso",
    "ano_inicio",
    "data_inscricao",
    "Área Principal (Objetiva)",
    "Score RH (%)",
    "Score Projetos (%)",
    "Score Training (%)",
    "Score Marketing (%)",
]
# Mantém apenas colunas existentes caso o CSV tenha variações
colunas_tabela = [c for c in colunas_tabela if c in df_exibido.columns]

st.dataframe(
    df_exibido[colunas_tabela],
    use_container_width=True,
    hide_index=True,
    column_config={
        "nome": "Nome",
        "email": "E-mail",
        "curso": "Curso",
        "ano_inicio": st.column_config.NumberColumn("Ano de Início", format="%d"),
        "data_inscricao": "Data de Inscrição",
        "Score RH (%)": st.column_config.ProgressColumn("RH (%)", min_value=0, max_value=100, format="%.1f%%"),
        "Score Projetos (%)": st.column_config.ProgressColumn("Projetos (%)", min_value=0, max_value=100, format="%.1f%%"),
        "Score Training (%)": st.column_config.ProgressColumn("Training (%)", min_value=0, max_value=100, format="%.1f%%"),
        "Score Marketing (%)": st.column_config.ProgressColumn("Marketing (%)", min_value=0, max_value=100, format="%.1f%%"),
    },
)

# --- DETALHAMENTO INDIVIDUAL DO CANDIDATO ---
if not df_exibido.empty:
    st.divider()
    st.subheader("Ficha Individual do Candidato")

    opcoes_candidatos = df_exibido["nome"] + " (" + df_exibido["email"] + ")"
    selecionado = st.selectbox("Selecione um candidato para ver os detalhes completos:", options=opcoes_candidatos)

    candidato = df_exibido[opcoes_candidatos == selecionado].iloc[0]

    c_dados, c_scores = st.columns([1, 1])
    with c_dados:
        st.markdown("**Dados Pessoais**")
        st.write(f"- **Nome:** {candidato.get('nome', '-')}")
        st.write(f"- **E-mail:** {candidato.get('email', '-')}")
        st.write(f"- **Curso:** {candidato.get('curso', '-')}")
        st.write(f"- **Ano de início:** {candidato.get('ano_inicio', '-')}")
        st.write(f"- **Inscrição em:** {candidato.get('data_inscricao', '-')}")

    with c_scores:
        st.markdown("**Pontuação Objetiva por Área**")
        for area in AREAS:
            st.write(f"- **{area}:** {candidato[f'Score {area} (%)']}%")
        st.info(f"**Indicação Objetiva:** {candidato['Área Principal (Objetiva)']}")