import os
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tickets.csv")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

PT_STOP_WORDS = [
    "a", "ao", "aos", "as", "até", "com", "como", "da", "das", "de", "dela",
    "delas", "dele", "deles", "depois", "do", "dos", "e", "ela", "elas", "ele",
    "eles", "em", "entre", "essa", "essas", "esse", "esses", "esta", "estas",
    "este", "estes", "eu", "foi", "há", "isso", "isto", "já", "mas", "me",
    "mesmo", "muito", "na", "nas", "nem", "no", "nos", "nós", "o", "os", "ou",
    "para", "pela", "pelas", "pelo", "pelos", "por", "porque", "que", "quem",
    "se", "sem", "ser", "seu", "seus", "só", "sua", "suas", "também", "tem",
    "ter", "um", "uma", "umas", "uns", "você", "vocês",
]


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=3000, stop_words=PT_STOP_WORDS)),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])


def main():
    df = pd.read_csv(DATA_PATH)
    print(f"Dataset: {len(df)} tickets\n")
    print("Distribuição por categoria:")
    print(df["categoria"].value_counts().to_string())
    print("\nDistribuição por prioridade:")
    print(df["prioridade"].value_counts().to_string())

    X = df["texto"]
    y_cat = df["categoria"]
    y_pri = df["prioridade"]

    X_train, X_test, y_cat_train, y_cat_test, y_pri_train, y_pri_test = train_test_split(
        X, y_cat, y_pri, test_size=0.2, random_state=42, stratify=y_cat
    )

    print(f"\nTreino: {len(X_train)} | Teste: {len(X_test)}")

    print("\n" + "=" * 60)
    print("CLASSIFICADOR DE CATEGORIA")
    print("=" * 60)
    cat_model = build_pipeline()
    cat_model.fit(X_train, y_cat_train)
    print(classification_report(y_cat_test, cat_model.predict(X_test)))

    print("=" * 60)
    print("CLASSIFICADOR DE PRIORIDADE")
    print("=" * 60)
    pri_model = build_pipeline()
    pri_model.fit(X_train, y_pri_train)
    print(classification_report(y_pri_test, pri_model.predict(X_test)))

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(cat_model, os.path.join(MODELS_DIR, "categoria_model.joblib"))
    joblib.dump(pri_model, os.path.join(MODELS_DIR, "prioridade_model.joblib"))
    print(f"Modelos salvos em '{MODELS_DIR}'")


if __name__ == "__main__":
    main()
