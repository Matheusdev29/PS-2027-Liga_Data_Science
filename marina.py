import json
from score import calcular_score, COLUNAS_VALORES

marina = {
    32: "3 - Neutro", 37: "3 - Neutro", 39: "3 - Neutro",          # RH
    33: "4 - Concordo", 35: "4 - Concordo", 43: "3 - Neutro",      # Projetos
    31: "3 - Neutro", 34: "3 - Neutro", 38: "3 - Neutro",          # Marketing
    36: "5 - Concordo totalmente", 40: "2 - Discordo", 42: "5 - Concordo totalmente",  # Training
}
marina.update({c: "4 - Concordo" for c in COLUNAS_VALORES})

print(json.dumps(calcular_score(marina), ensure_ascii=False, indent=2))