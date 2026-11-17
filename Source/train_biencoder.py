import json
from pathlib import Path

import pandas as pd
import torch
import torch.nn.functional as F
from torch import nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

try:
    from Source.namematching import normalize_name
except Exception:
    try:
        from namematching import normalize_name
    except Exception:
        def normalize_name(value: str) -> str:
            return str(value)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = Path("./outputs/biencoder")
TRAIN_PATH = Path("data/train.csv")


class NamePairDataset(Dataset):
    def __init__(self, df, tokenizer, max_len=64, normalize_inputs=True):
        self.df = df
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.normalize_inputs = normalize_inputs

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        name_a = "" if pd.isna(row["name_a"]) else str(row["name_a"])
        name_b = "" if pd.isna(row["name_b"]) else str(row["name_b"])
        if self.normalize_inputs:
            normalized_a = normalize_name(name_a)
            normalized_b = normalize_name(name_b)
            if normalized_a.strip():
                name_a = normalized_a
            if normalized_b.strip():
                name_b = normalized_b
        enc_a = self.tokenizer(
            name_a,
            padding="max_length",
            truncation=True,
            max_length=self.max_len,
            return_tensors="pt",
        )
        enc_b = self.tokenizer(
            name_b,
            padding="max_length",
            truncation=True,
            max_length=self.max_len,
            return_tensors="pt",
        )
        return {
            "input_ids_a": enc_a["input_ids"].squeeze(),
            "attention_mask_a": enc_a["attention_mask"].squeeze(),
            "input_ids_b": enc_b["input_ids"].squeeze(),
            "attention_mask_b": enc_b["attention_mask"].squeeze(),
            "label": torch.tensor(row["label"], dtype=torch.float),
        }


class BiEncoder(nn.Module):
    def __init__(self, model_name):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)

    def encode(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        mask = attention_mask.unsqueeze(-1).expand(out.last_hidden_state.size()).float()
        summed = torch.sum(out.last_hidden_state * mask, dim=1)
        counts = torch.clamp(mask.sum(dim=1), min=1e-9)
        pooled = summed / counts
        return F.normalize(pooled, p=2, dim=1)

    def forward(self, batch):
        emb_a = self.encode(batch["input_ids_a"], batch["attention_mask_a"])
        emb_b = self.encode(batch["input_ids_b"], batch["attention_mask_b"])
        return emb_a, emb_b


def contrastive_loss(emb_a, emb_b, labels, margin=0.5):
    cosine_sim = F.cosine_similarity(emb_a, emb_b)
    pos_loss = labels * (1 - cosine_sim)
    neg_loss = (1 - labels) * torch.clamp(cosine_sim - margin, min=0)
    return (pos_loss + neg_loss).mean()


def _find_best_threshold(scores: list[float], labels: list[int]) -> tuple[float, dict[str, float]]:
    if not scores or len(scores) != len(labels):
        return 0.75, {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }

    thresholds = sorted(set(float(score) for score in scores))
    best_threshold = thresholds[0]
    best_metrics = {
        "accuracy": 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "f1": -1.0,
    }

    for threshold in thresholds:
        tp = fp = tn = fn = 0
        for score, label in zip(scores, labels):
            pred = 1 if score >= threshold else 0
            if pred == 1 and label == 1:
                tp += 1
            elif pred == 1 and label == 0:
                fp += 1
            elif pred == 0 and label == 0:
                tn += 1
            else:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        accuracy = (tp + tn) / max(1, len(scores))
        candidate_metrics = {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
        }

        if (
            candidate_metrics["f1"] > best_metrics["f1"]
            or (
                candidate_metrics["f1"] == best_metrics["f1"]
                and candidate_metrics["accuracy"] > best_metrics["accuracy"]
            )
        ):
            best_threshold = threshold
            best_metrics = candidate_metrics

    return float(best_threshold), best_metrics


def evaluate_model(model, loader, margin=0.5):
    model.eval()
    total_loss = 0.0
    total_batches = 0
    scores: list[float] = []
    labels: list[int] = []

    with torch.no_grad():
        for batch in loader:
            for key in batch:
                batch[key] = batch[key].to(DEVICE)

            emb_a, emb_b = model(batch)
            loss = contrastive_loss(emb_a, emb_b, batch["label"], margin=margin)
            similarities = F.cosine_similarity(emb_a, emb_b)

            total_loss += float(loss.item())
            total_batches += 1
            scores.extend(float(score) for score in similarities.detach().cpu().tolist())
            labels.extend(int(label) for label in batch["label"].detach().cpu().tolist())

    threshold, metrics = _find_best_threshold(scores, labels)
    metrics["loss"] = total_loss / max(1, total_batches)
    metrics["threshold"] = threshold
    return metrics


def _save_training_summary(summary: dict[str, object], output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def clean_pairs(df: pd.DataFrame) -> pd.DataFrame:
    df = df.loc[:, ["name_a", "name_b", "label"]].copy()
    df["name_a"] = df["name_a"].fillna("").astype(str)
    df["name_b"] = df["name_b"].fillna("").astype(str)
    df["label"] = pd.to_numeric(df["label"], errors="coerce")
    return df[df["label"].isin([0, 1])].copy()


def make_loader(df: pd.DataFrame, tokenizer, shuffle: bool = False) -> DataLoader:
    return DataLoader(NamePairDataset(df, tokenizer), batch_size=32, shuffle=shuffle)


def main(
    train_path: Path | None = None,
    output_dir: Path | None = None,
    base_model: str | None = None,
    epochs: int = 5,
    lr: float = 2e-5,
    val_df: pd.DataFrame | None = None,
):
    """Train the bi-encoder.

    base_model: start from this checkpoint (e.g. the live model) instead of the stock MiniLM.
    val_df: fixed holdout; when given, all rows of the training CSV are used for training.
    """
    train_path = Path(train_path) if train_path else TRAIN_PATH
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    start_model = base_model or MODEL_NAME

    if not train_path.exists():
        raise FileNotFoundError(f"Training data not found: {train_path}")

    df = pd.read_csv(train_path)
    required_columns = {"name_a", "name_b", "label"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Training CSV is missing required columns: {sorted(missing_columns)}")

    df = clean_pairs(df)
    if df.empty:
        raise ValueError("Training CSV does not contain any valid 0/1 labels.")

    if val_df is not None:
        train_df, val_df = df, clean_pairs(val_df)
    else:
        from sklearn.model_selection import train_test_split

        stratify_labels = df["label"] if df["label"].nunique() > 1 else None
        train_df, val_df = train_test_split(
            df,
            test_size=0.1,
            random_state=42,
            stratify=stratify_labels,
        )

    tok_source = start_model if (Path(start_model) / "tokenizer_config.json").exists() else MODEL_NAME
    tokenizer = AutoTokenizer.from_pretrained(tok_source)

    train_loader = make_loader(train_df, tokenizer, shuffle=True)
    val_loader = make_loader(val_df, tokenizer)

    model = BiEncoder(start_model).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    best_val_f1 = -1.0
    best_summary: dict[str, object] | None = None

    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch in train_loader:
            for k in batch:
                batch[k] = batch[k].to(DEVICE)

            emb_a, emb_b = model(batch)
            loss = contrastive_loss(emb_a, emb_b, batch["label"])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        train_loss = total_loss / max(1, len(train_loader))
        val_metrics = evaluate_model(model, val_loader)
        print(
            f"Epoch {epoch + 1} - Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_metrics['loss']:.4f} | "
            f"Val F1: {val_metrics['f1']:.4f} | "
            f"Val Acc: {val_metrics['accuracy']:.4f} | "
            f"Best Threshold: {val_metrics['threshold']:.4f}"
        )

        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = float(val_metrics["f1"])
            output_dir.mkdir(parents=True, exist_ok=True)
            model.encoder.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)
            best_summary = {
                "model_name": start_model,
                "device": DEVICE,
                "train_rows": int(len(train_df)),
                "val_rows": int(len(val_df)),
                "best_epoch": int(epoch + 1),
                "best_threshold": float(val_metrics["threshold"]),
                "metrics": {
                    "train_loss": float(train_loss),
                    "val_loss": float(val_metrics["loss"]),
                    "val_accuracy": float(val_metrics["accuracy"]),
                    "val_precision": float(val_metrics["precision"]),
                    "val_recall": float(val_metrics["recall"]),
                    "val_f1": float(val_metrics["f1"]),
                },
                "pooling": "mean",
                "normalization": "Source.namematching.normalize_name",
            }
            _save_training_summary(best_summary, output_dir)

    if best_summary is None:
        raise RuntimeError("Training completed without producing a valid checkpoint.")

    print(f"Best model saved to {output_dir}")
    print(
        "Recommended threshold: "
        f"{float(best_summary['best_threshold']):.4f} "
        f"(epoch {int(best_summary['best_epoch'])})"
    )
    return best_summary


if __name__ == "__main__":
    main()
