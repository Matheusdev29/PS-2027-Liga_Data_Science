import hmac
import pandas as pd
import streamlit as st

from core.dados import ler_inscricoes
from score import calcular_score

AREAS = ["RH", "Projetos", "Training", "Marketing"]

MAPA_FORM_PARA_SCORE = {
    "obj_1": [32],
    "obj_6": [37],
    "obj_2": [33],
    "obj_5": [35],
    "obj_3": [36],
    "obj_4": [34],
    "obj_7": [40, 31],
}


def verificar_autenticacao() -> bool:
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


def carregar_dados(arquivo_upload) -> pd.DataFrame:
    """Lê o CSV enviado por upload ou busca os dados da planilha via ler_inscricoes()."""
    if arquivo_upload is not None:
        return pd.read_csv(arquivo_upload)
    return ler_inscricoes()


def garantir_pontuacoes(df: pd.DataFrame) -> pd.DataFrame:
    """Converte as pontuações vindas da planilha para numérico ou calcula via calcular_score."""
    df_calc = df.copy()
    colunas_score = ["Pontos_RH", "Pontos_Projetos", "Pontos_Training", "Pontos_Marketing"]

    if all(col in df_calc.columns for col in colunas_score):
        for col in colunas_score:
            df_calc[col] = pd.to_numeric(df_calc[col], errors="coerce").fillna(0)
        if "Area_Sugerida" not in df_calc.columns:
            mapa_nomes = {
                "Pontos_RH": "RH",
                "Pontos_Projetos": "Projetos",
                "Pontos_Training": "Training",
                "Pontos_Marketing": "Marketing",
            }
            df_calc["Area_Sugerida"] = df_calc[colunas_score].idxmax(axis=1).map(mapa_nomes)
        return df_calc

    # Fallback: calcula via calcular_score() se o CSV enviado não tiver as colunas prontas
    resultados = []
    for _, row in df_calc.iterrows():
        respostas_score = {}
        for chave, colunas in MAPA_FORM_PARA_SCORE.items():
            if chave in df_calc.columns:
                for col in colunas:
                    respostas_score[col] = row[chave]
        resultados.append(calcular_score(respostas_score))

    df_calc["Pontos_RH"] = [r["pontos"]["rh"] for r in resultados]
    df_calc["Pontos_Projetos"] = [r["pontos"]["projetos"] for r in resultados]
    df_calc["Pontos_Training"] = [r["pontos"]["training"] for r in resultados]
    df_calc["Pontos_Marketing"] = [r["pontos"]["marketing"] for r in resultados]
    df_calc["Area_Sugerida"] = [r["area_sugerida"] or "Indefinida" for r in resultados]
    return df_calc


# --- BLOQUEIO POR SENHA ---
if not verificar_autenticacao():
    st.stop()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configurações do Painel")

    arquivo_upload = st.file_uploader(
        "Carregar arquivo CSV (opcional)",
        type=["csv"],
        help="Se nenhum arquivo for enviado, o painel lê diretamente do Google Sheets.",
    )

    if st.button("Atualizar dados da planilha", use_container_width=True):
        ler_inscricoes.clear()
        st.rerun()

    st.divider()
    area_filtro = st.selectbox("Filtrar por Área", options=["Todas"] + AREAS)

    st.divider()
    if st.button("Sair do Painel", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

# --- CORPO PRINCIPAL ---
st.title("Painel de Avaliação — Processo Seletivo")

try:
    df_raw = carregar_dados(arquivo_upload)
except Exception as erro:
    st.error(f"Erro ao carregar inscrições: {erro}")
    st.stop()

if df_raw is None or df_raw.empty:
    st.warning("Nenhuma inscrição encontrada no momento.")
    st.stop()

fonte_atual = f"Upload: `{arquivo_upload.name}`" if arquivo_upload else "Google Sheets (`ler_inscricoes`)"
st.caption(f"Fonte de dados ativa: {fonte_atual}")

df = garantir_pontuacoes(df_raw)

# Botão de download na sidebar com os dados carregados
with st.sidebar:
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="Baixar dados em CSV",
        data=csv_bytes,
        file_name="inscricoes_processo_seletivo.csv",
        mime="text/csv",
        use_container_width=True,
    )

# Filtro por área
coluna_area_filtro = {
    "RH": "Pontos_RH",
    "Projetos": "Pontos_Projetos",
    "Training": "Pontos_Training",
    "Marketing": "Pontos_Marketing",
}

if area_filtro != "Todas":
    df_exibido = df[df["Area_Sugerida"] == area_filtro].sort_values(
        by=coluna_area_filtro[area_filtro], ascending=False
    )
else:
    df_exibido = df.copy()

# --- CONTADORES (KPIs) ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total de Candidaturas", len(df))
for idx, area in enumerate(AREAS, start=2):
    qtd_area = int((df["Area_Sugerida"] == area).sum())
    locals()[f"col{idx}"].metric(f"Afinidade: {area}", qtd_area)

st.divider()

# --- TABELA GERAL ---
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
    "Area_Sugerida",
    "Pontos_RH",
    "Pontos_Projetos",
    "Pontos_Training",
    "Pontos_Marketing",
]
colunas_tabela = [c for c in colunas_tabela if c in df_exibido.columns]

st.dataframe(
    df_exibido[colunas_tabela],
    use_container_width=True,
    hide_index=True,
    column_config={
        "nome": "Nome",
        "email": "E-mail",
        "curso": "Curso",
        "ano_inicio": "Ano de Início",
        "data_inscricao": "Data de Inscrição",
        "Area_Sugerida": "Área Sugerida",
        "Pontos_RH": st.column_config.NumberColumn("RH (pts)", format="%.1f"),
        "Pontos_Projetos": st.column_config.NumberColumn("Projetos (pts)", format="%.1f"),
        "Pontos_Training": st.column_config.NumberColumn("Training (pts)", format="%.1f"),
        "Pontos_Marketing": st.column_config.NumberColumn("Marketing (pts)", format="%.1f"),
    },
)

# --- FICHA INDIVIDUAL ---
if not df_exibido.empty:
    st.divider()
    st.subheader("Ficha Individual do Candidato")

    opcoes_candidatos = df_exibido["nome"].astype(str) + " (" + df_exibido["email"].astype(str) + ")"
    selecionado = st.selectbox("Selecione um candidato:", options=opcoes_candidatos)
    candidato = df_exibido[opcoes_candidatos == selecionado].iloc[0]

    c_dados, c_scores = st.columns(2)
    with c_dados:
        st.markdown("**Dados Pessoais**")
        st.write(f"- **Nome:** {candidato.get('nome', '-')}")
        st.write(f"- **E-mail:** {candidato.get('email', '-')}")
        st.write(f"- **Curso:** {candidato.get('curso', '-')}")
        st.write(f"- **Ano de início:** {candidato.get('ano_inicio', '-')}")
        st.write(f"- **Inscrição em:** {candidato.get('data_inscricao', '-')}")

    with c_scores:
        st.markdown("**Pontuação Objetiva por Área (`calcular_score`)**")
        st.write(f"- **RH:** {candidato['Pontos_RH']} pts")
        st.write(f"- **Projetos:** {candidato['Pontos_Projetos']} pts")
        st.write(f"- **Training:** {candidato['Pontos_Training']} pts")
        st.write(f"- **Marketing:** {candidato['Pontos_Marketing']} pts")
        if candidato.get("Penalizacoes"):
            st.warning(f"**Penalizações aplicadas:** {candidato['Penalizacoes']}")
        st.info(f"**Área Sugerida:** {candidato['Area_Sugerida']}")