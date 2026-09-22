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

pg = st.navigation(
    {
        "Inicio": [pagina_inicio],
        "Formulário": [pagina_formulario],
    }
)

pg.run()