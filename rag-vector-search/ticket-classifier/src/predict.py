import os
import sys
import argparse
import joblib

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

CATEGORIA_DESC = {
    "incidente":      "Incidente — algo parou ou está errado em produção",
    "duvida":         "Dúvida — orientação sobre uso do que foi entregue",
    "manutencao":     "Manutenção — ajuste dentro do escopo do contrato",
    "fora_de_escopo": "Fora de escopo — nova demanda, virar proposta comercial",
}

PRIORIDADE_DESC = {
    "alta":  "Alta  — responder em até 4h",
    "media": "Média — responder em até 24h",
    "baixa": "Baixa — responder em até 48h",
}


def main():
    parser = argparse.ArgumentParser(description="Classificador de tickets de suporte Datalyx")
    parser.add_argument("--text", required=True, help="Texto do ticket")
    args = parser.parse_args()

    cat_path = os.path.join(MODELS_DIR, "categoria_model.joblib")
    pri_path = os.path.join(MODELS_DIR, "prioridade_model.joblib")

    if not os.path.exists(cat_path):
        print("Modelo não encontrado. Execute primeiro: python src/train.py")
        sys.exit(1)

    cat_model = joblib.load(cat_path)
    pri_model = joblib.load(pri_path)

    categoria = cat_model.predict([args.text])[0]
    prioridade = pri_model.predict([args.text])[0]

    cat_proba = dict(zip(cat_model.classes_, cat_model.predict_proba([args.text])[0]))
    pri_proba = dict(zip(pri_model.classes_, pri_model.predict_proba([args.text])[0]))

    print("\n" + "=" * 60)
    print("CLASSIFICAÇÃO DO TICKET")
    print("=" * 60)
    print(f"\nTicket: {args.text}\n")
    print(f"Categoria  : {CATEGORIA_DESC.get(categoria, categoria)}")
    print(f"Prioridade : {PRIORIDADE_DESC.get(prioridade, prioridade)}")

    print("\nConfiança por categoria:")
    for cls, prob in sorted(cat_proba.items(), key=lambda x: -x[1]):
        bar = "#" * int(prob * 20)
        print(f"  {cls:<20} {bar:<20} {prob:.0%}")

    print("\nConfiança por prioridade:")
    for cls, prob in sorted(pri_proba.items(), key=lambda x: -x[1]):
        bar = "#" * int(prob * 20)
        print(f"  {cls:<20} {bar:<20} {prob:.0%}")

    if categoria == "fora_de_escopo":
        print("\n>> Acao: encaminhar para time comercial — nova proposta necessaria.")
    elif categoria == "incidente" and prioridade == "alta":
        print("\n>> Acao: acionar responsavel tecnico imediatamente.")

    print()


if __name__ == "__main__":
    main()
