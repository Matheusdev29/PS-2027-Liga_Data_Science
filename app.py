import streamlit as st

pagina_inicio = st.Page(
    page="paginas/inicio.py",
    title="Orientações",
    default=True
)

pagina_formulario = st.Page(
    page="paginas/formulario.py",
    title="Formulário"
)

pagina_painel = st.Page(
    page="paginas/painel.py",
    title="Painel"
)

pg = st.navigation(
    {
        "Inicio": [pagina_inicio],
        "Formulário": [pagina_formulario],
        "Painel": [pagina_painel]
    }
)

pg.run()