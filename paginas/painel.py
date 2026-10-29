import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="ánalise de score dos candidatos", layout="wide"
)
st.title("Painel de Ànalise dos candidatos")

uploaded_file = st.sidebar.file_uploader("envie seu arquivo", type=["csv"])
if uploaded_file is None :
  dados ={
    "Nome":["matheus", "andrei", "leticia", "isabela", "giulia"],
    "Area":["RH", "Projetos", "Marketing", "training", "RH"],
    "Score":[10, 11, 12, 13, 14]
  }
  df = pd.DataFrame(dados)
else:
  df = pd.read_csv(uploaded_file, sep=None, engine="python", encoding="utf-8-sig")

df.columns = df.columns.str.strip()

colunas_necessarias = {"Nome", "Area", "Score"}
if not colunas_necessarias.issubset(set(df.columns)):
    colunas_encontradas = ", ".join([f"'{c}'" for c in df.columns])
    st.error(
        f"❌ O arquivo CSV precisa conter as colunas **Nome**, **Area** e **Score**.\n\n"
        f"**Colunas encontradas no seu CSV:** {colunas_encontradas}"
    )
else:
    st.markdown("---")

areas_unicas = list(df["Area"].dropna().unique())
opcao_area = st.selectbox(
        "🎯 Escolha a área que deseja analisar:",
        options= areas_unicas
    )
df_filtrado = df[df["Area"] == opcao_area]

    # Ordena automaticamente pelo maior Score no topo
df_filtrado = df_filtrado.sort_values(by="Score", ascending=False)

st.subheader("Resultados")



    # Exibe a tabela apenas com Nome e Score
st.dataframe(
        df_filtrado[["Nome", "Score"]],
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score",
                help="Score individual da pessoa",
                format="%d",
                min_value=0,
                max_value=int(df["Score"].max() if df["Score"].max() > 0 else 100),
            ),
        },
        use_container_width=True,
        hide_index=True
    )