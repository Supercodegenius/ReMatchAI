import os
import pandas as pd
from datasets import Dataset
from sklearn.model_selection import train_test_split

import torch
from torch import nn
from transformers import (
    AutoTokenizer,
    AutoModel,
    Trainer,
    TrainingArguments,
)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # small, fast

class NameMatchModel(nn.Module):
    def __init__(self, model_name):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, 2)  # 2 classes: no-match, match
        )

    def forward(self, input_ids, attention_mask, labels=None):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        # CLS token representation
        cls_emb = outputs.last_hidden_state[:, 0, :]
        logits = self.classifier(cls_emb)

        loss = None
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits, labels)

        return {"loss": loss, "logits": logits}


def load_data(csv_path):
    df = pd.read_csv(csv_path)
    # basic cleaning if needed
    df["name_a"] = df["name_a"].astype(str).str.strip()
    df["name_b"] = df["name_b"].astype(str).str.strip()
    return df


def make_hf_dataset(df):
    return Dataset.from_pandas(df)


def main():
    train_df = load_data("data/train.csv")
    val_df = load_data("data/val.csv")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def preprocess(batch):
        texts = [
            f"{a} [SEP] {b}"
            for a, b in zip(batch["name_a"], batch["name_b"])
        ]
        enc = tokenizer(
            texts,
            padding="max_length",
            truncation=True,
            max_length=64,
        )
        enc["labels"] = batch["label"]
        return enc

    train_ds = make_hf_dataset(train_df).map(preprocess, batched=True)
    val_ds = make_hf_dataset(val_df).map(preprocess, batched=True)

    train_ds.set_format(
        type="torch",
        columns=["input_ids", "attention_mask", "labels"],
    )
    val_ds.set_format(
        type="torch",
        columns=["input_ids", "attention_mask", "labels"],
    )

    model = NameMatchModel(MODEL_NAME)

    training_args = TrainingArguments(
        output_dir="./outputs/name_match_model",
        num_train_epochs=5,
        per_device_train_batch_size=32,
        per_device_eval_batch_size=64,
        learning_rate=2e-5,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        logging_steps=50,
        save_total_limit=2,
    )

    def compute_metrics(eval_pred):
        from sklearn.metrics import precision_recall_fscore_support, accuracy_score
        logits, labels = eval_pred
        preds = logits.argmax(axis=-1)
        acc = accuracy_score(labels, preds)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, preds, average="binary"
        )
        return {
            "accuracy": acc,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model("./outputs/name_match_model")
    tokenizer.save_pretrained("./outputs/name_match_model")


if __name__ == "__main__":
    main()