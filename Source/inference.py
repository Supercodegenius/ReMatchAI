import torch
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F

MODEL_DIR = "./outputs/biencoder"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
encoder = AutoModel.from_pretrained(MODEL_DIR).to(DEVICE)
encoder.eval()


def _mean_pool(last_hidden_state, attention_mask):
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    summed = torch.sum(last_hidden_state * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


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
        pooled = _mean_pool(out.last_hidden_state, enc["attention_mask"])
        return F.normalize(pooled, p=2, dim=1).cpu().numpy()[0]


def match_score(name_a, name_b):
    emb_a = embed(name_a)
    emb_b = embed(name_b)
    return float((emb_a * emb_b).sum())  # cosine similarity


if __name__ == "__main__":
    s = match_score("AXA XL Reinsurance Ltd", "AXA XL Re")
    print("Similarity:", s)