from score import avaliar_planilha

url = "https://docs.google.com/spreadsheets/d/1xytU497CeHlK23ZKKJLBy7a23-mA2qDwQhFCVEOZnmI/edit?resourcekey=&gid=1513164428#gid=1513164428"

df = avaliar_planilha(url, pausa=0.5)
df.to_csv("resultado.csv", index=False, encoding="utf-8-sig")