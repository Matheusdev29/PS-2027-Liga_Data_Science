import streamlit as st

st.markdown(
    """
<style>
h1 { color: #0C6980 !important; }
h2, h3 { color: #0C6980 !important; }

.destaque {
    background-color: #FFE684;
    border-left: 8px solid #FED531;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin: 1rem 0 1.5rem 0;
}
.destaque h3 { margin-top: 0; }

[data-testid="stPageLink"] a {
    background-color: #FED531;
    color: #1A1A1A !important;
    font-weight: 600;
    padding: 0.6rem 1.4rem;
    border-radius: 0.6rem;
    text-decoration: none;
}
[data-testid="stPageLink"] a:hover { background-color: #FFE684; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Processo Seletivo 2027")
st.caption("Liga de Data Science · UNICAMP")

st.markdown(
    """
<div class="destaque">
  <h3>Inscrições abertas de 09/03 a 20/03/2027</h3>
  A inscrição leva cerca de 15 minutos. Responda com sinceridade: o questionário
  serve para entendermos com qual área você tem mais afinidade.
  <b>Não existe resposta certa.</b>
</div>
""",
    unsafe_allow_html=True,
)

st.subheader("Como funciona")
st.markdown(
    """
1. Dados pessoais e curso
2. 10 perguntas sobre os valores da Liga (escala de 1 a 5)
3. 12 perguntas de afinidade com as áreas: Marketing, Projetos, RH e Training (escala de 1 a 5)
4. 3 perguntas dissertativas curtas
5. Você recebe uma confirmação na tela e o RH entra em contato pelo e-mail informado
"""
)

st.subheader("Orientações")
st.markdown(
    """
- Preencha tudo de uma vez: ao enviar, o formulário **não pode ser editado**.
- Use o e-mail que você mais acessa, pois é por ele que vamos falar com você.
- Nas perguntas de 1 a 5, **1 = Discordo totalmente** e **5 = Concordo totalmente**.
- Nas dissertativas, seja objetivo(a) e conte exemplos reais.
"""
)

st.page_link("paginas/formulario.py", label="Começar inscrição")

st.caption("Dúvidas: psdatascience84@gmail.com")