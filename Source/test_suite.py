import pandas as pd
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import precision_recall_fscore_support
import unicodedata, re, faiss, os
from pathlib import Path
from transformers import AutoTokenizer, AutoModel

# ---------------------------------------------------------
# 1. Normalisation Rules (Reinsurance-specific)
# ---------------------------------------------------------

LEGAL_SUFFIXES = [
    "ltd","limited","plc","llc","inc","corp","co","company",
    "ag","sa","s.a.","s.a","spa","gmbh","bv","nv","oy","ab",
    "pte","pvt","kg","kgaa","sas","sarl","llp","lp"
]

REINSURANCE_TERMS = [
    "reinsurance","reinsurance company","reinsurance co",
    "re","re.","reins","reins.","reassurance",
    "underwriting","insurance","insurance company",
    "branch","uk branch","europe sa","europe s.a."
]

COUNTRY_TERMS = ["uk","usa","us","eu","emea","asia","europe"]

def clean_text(s):
    s = s.lower().strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def remove_terms(s, terms):
    tokens = s.split()
    return " ".join([t for t in tokens if t not in terms])

def normalise_name(name):
    s = clean_text(name)
    s = remove_terms(s, LEGAL_SUFFIXES)
    s = remove_terms(s, REINSURANCE_TERMS)
    s = remove_terms(s, COUNTRY_TERMS)
    return " ".join(s.split())

# ---------------------------------------------------------
# 2. Load Bi-Encoder Model
# ---------------------------------------------------------

def resolve_model_dir() -> str:
    script_dir = Path(__file__).resolve().parent
    candidates = [
        Path("./outputs/biencoder"),
        script_dir / "outputs" / "biencoder",
        script_dir.parent / "outputs" / "biencoder",
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return str(candidate.resolve())

    checked = "\n".join(f"- {c.resolve()}" for c in candidates)
    raise FileNotFoundError(
        "Could not find local model directory for the bi-encoder.\n"
        "Expected one of these locations:\n"
        f"{checked}\n"
        "Please train/export the model first or update MODEL_DIR in test_suite.py."
    )


MODEL_DIR = resolve_model_dir()
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
encoder = AutoModel.from_pretrained(MODEL_DIR).to(DEVICE)
encoder.eval()

def embed(name):
    enc = tokenizer(
        name,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=64,
    )
    for k in enc:
        enc[k] = enc[k].to(DEVICE)

    with torch.no_grad():
        out = encoder(**enc)
        cls = out.last_hidden_state[:, 0, :]
        return F.normalize(cls, p=2, dim=1).cpu().numpy()[0]

def match_score(a, b):
    ea = embed(normalise_name(a))
    eb = embed(normalise_name(b))
    return float((ea * eb).sum())

# ---------------------------------------------------------
# 3. Test Categories
# ---------------------------------------------------------

def test_sanity():
    tests = [
        ("AXA XL Reinsurance Ltd", "AXA XL Re", 1),
        ("Munich Reinsurance Company", "Munchener Ruckversicherungs AG", 1),
        ("Swiss Re Europe SA", "Allianz SE", 0),
    ]
    print("\n--- SANITY TESTS ---")
    for a, b, exp in tests:
        s = match_score(a, b)
        print(f"{a} | {b} | score={s:.3f} | expected={exp}")

def test_normalisation():
    print("\n--- NORMALISATION TEST ---")
    a = "Swiss Re Europe S.A. (UK Branch)"
    b = "Swiss Re Europe SA"
    print("A_norm:", normalise_name(a))
    print("B_norm:", normalise_name(b))
    print("Score:", match_score(a, b))

def test_eval_set():
    if not os.path.exists("eval.csv"):
        print("\nNo eval.csv found — skipping evaluation test.")
        return

    print("\n--- EVALUATION SET TEST ---")
    df = pd.read_csv("eval.csv")
    preds = []
    for _, row in df.iterrows():
        score = match_score(row["name_a"], row["name_b"])
        preds.append(1 if score > 0.5 else 0)

    precision, recall, f1, _ = precision_recall_fscore_support(
        df["label"], preds, average="binary"
    )
    print("Precision:", precision)
    print("Recall:", recall)
    print("F1:", f1)

def test_hard_negatives():
    print("\n--- HARD NEGATIVE TESTS ---")
    tests = [
        ("Allianz SE", "Allianz Global Corporate & Specialty SE"),
        ("Swiss Re", "Swiss Life"),
        ("Munich Re", "Munich Health"),
    ]
    for a, b in tests:
        print(a, "|", b, "| score:", match_score(a, b))

def test_noise():
    print("\n--- NOISE ROBUSTNESS TESTS ---")
    tests = [
        ("Munich Re", "Munch Re"),
        ("Hannover Re", "Hann0ver Re"),
        ("SCOR SE", "S C O R"),
    ]
    for a, b in tests:
        print(a, "|", b, "| score:", match_score(a, b))

def test_faiss():
    if not os.path.exists("reinsurance_index.faiss"):
        print("\nFAISS index not found — skipping FAISS test.")
        return

    print("\n--- FAISS SEARCH TEST ---")
    index = faiss.read_index("reinsurance_index.faiss")
    names = open("all_names.txt").read().splitlines()

    q = "AXA XL Re"
    q_emb = embed(q).astype("float32")

    D, I = index.search(np.array([q_emb]), k=5)

    for score, idx in zip(D[0], I[0]):
        print(score, names[idx])

# ---------------------------------------------------------
# 4. Run All Tests
# ---------------------------------------------------------

if __name__ == "__main__":
    print("\n==============================")
    print(" REINSURANCE NAME MATCHING TEST SUITE")
    print("==============================")

    test_sanity()
    test_normalisation()
    test_eval_set()
    test_hard_negatives()
    test_noise()
    test_faiss()

    print("\nAll tests completed.")