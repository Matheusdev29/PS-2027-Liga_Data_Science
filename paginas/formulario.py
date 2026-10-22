import streamlit as st
import pandas as pd
st.title("Formulário")
st.write("Responda com sinceridade")


df = pd.DataFrame({
    'coluna': [1,2,3,4]
})

st.set_page_config(
    layout="centered"
)
st.title("Processo Seletivo")
nome = st.text_input("Digite seu nome:")

expectativa = st.text_area("o que te motiva a entrar na Liga?")

option = st.selectbox('de 1 a 5 o quanto você gosta de trabalha em grupo?', df['coluna'])

nivel = st.select_slider("o quanto você é paciente", options=["Extremamente", "Muito", "Médio", "Pouco"])
PS = st.form('processo')
submit = PS.form_submit_button("enviar formulario")

if submit:
    st.write('voce escolheu:', option)
    st.write('Sua paciência:', nivel)
    st.write('seu nome:', nome)
