import hmac
import pandas as pd
import streamlit as st

from core.dados import ler_inscricoes
from core.perguntas import montar_respostas_score
from score import calcular_score

AREAS = ["RH", "Projetos", "Training", "Marketing"]


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
        if "Fit_Pontos" in df_calc.columns:
            df_calc["Fit_Pontos"] = pd.to_numeric(df_calc["Fit_Pontos"], errors="coerce").fillna(0)
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
    resultados = [
        calcular_score(montar_respostas_score(row.to_dict())) for _, row in df_calc.iterrows()
    ]

    df_calc["Pontos_RH"] = [r["pontos"]["rh"] for r in resultados]
    df_calc["Pontos_Projetos"] = [r["pontos"]["projetos"] for r in resultados]
    df_calc["Pontos_Training"] = [r["pontos"]["training"] for r in resultados]
    df_calc["Pontos_Marketing"] = [r["pontos"]["marketing"] for r in resultados]
    df_calc["Area_Sugerida"] = [r["area_sugerida"] or "Indefinida" for r in resultados]
    df_calc["Fit_Valores"] = ["Sim" if r["fit"] else "Não" for r in resultados]
    df_calc["Fit_Pontos"] = [r["fit_pontos"] for r in resultados]
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
    fit_filtro = st.selectbox("Fit de valores", options=["Todos", "Sim", "Não"])

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

# Filtros e ordenação
coluna_area_filtro = {
    "RH": "Pontos_RH",
    "Projetos": "Pontos_Projetos",
    "Training": "Pontos_Training",
    "Marketing": "Pontos_Marketing",
}
colunas_pontos = list(coluna_area_filtro.values())

df_exibido = df.copy()

if area_filtro != "Todas":
    df_exibido = df_exibido[df_exibido["Area_Sugerida"] == area_filtro]
    df_exibido = df_exibido.sort_values(by=coluna_area_filtro[area_filtro], ascending=False)
else:
    # Sem filtro de área: ordena pela maior pontuação entre as 4 áreas
    df_exibido = df_exibido.assign(_maior=df_exibido[colunas_pontos].max(axis=1))
    df_exibido = df_exibido.sort_values(by="_maior", ascending=False).drop(columns="_maior")

if fit_filtro != "Todos":
    if "Fit_Valores" in df_exibido.columns:
        df_exibido = df_exibido[df_exibido["Fit_Valores"] == fit_filtro]
    else:
        st.sidebar.warning("Os dados carregados não têm a coluna Fit_Valores.")

# --- CONTADORES (KPIs) ---
colunas_kpi = st.columns(5)
colunas_kpi[0].metric("Total de Candidaturas", len(df))
for coluna_kpi, area in zip(colunas_kpi[1:], AREAS):
    qtd_area = int((df["Area_Sugerida"] == area).sum())
    coluna_kpi.metric(f"Afinidade: {area}", qtd_area)

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
    "Fit_Valores",
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
        "Fit_Valores": "Fit de valores",
        "Area_Sugerida": "Área Sugerida",
        "Pontos_RH": st.column_config.ProgressColumn("RH", min_value=0, max_value=15, format="%.0f/15"),
        "Pontos_Projetos": st.column_config.ProgressColumn("Projetos", min_value=0, max_value=15, format="%.0f/15"),
        "Pontos_Training": st.column_config.ProgressColumn("Training", min_value=0, max_value=15, format="%.0f/15"),
        "Pontos_Marketing": st.column_config.ProgressColumn("Marketing", min_value=0, max_value=15, format="%.0f/15"),
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
        if candidato.get("Fit_Valores"):
            st.write(f"- **Fit de valores:** {candidato['Fit_Valores']} ({candidato.get('Fit_Pontos', '-')}/50 pts)")
        if candidato.get("Penalizacoes"):
            st.warning(f"**Penalizações aplicadas:** {candidato['Penalizacoes']}")
        st.info(f"**Área Sugerida:** {candidato['Area_Sugerida']}")