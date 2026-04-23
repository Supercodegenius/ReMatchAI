import torch
from transformers import AutoTokenizer, AutoModel
from torch import nn

MODEL_DIR = "./outputs/name_match_model"

class NameMatchModel(nn.Module):
    def __init__(self, model_dir):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_dir)
        hidden_size = self.encoder.config.hidden_size
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, 2)
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls_emb = outputs.last_hidden_state[:, 0, :]
        logits = self.classifier(cls_emb)
        return logits


tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = NameMatchModel(MODEL_DIR)
model.eval()

def match_probability(name_a, name_b):
    text = f"{name_a} [SEP] {name_b}"
    enc = tokenizer(
        text,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=64,
    )
    with torch.no_grad():
        logits = model(enc["input_ids"], enc["attention_mask"])
        probs = torch.softmax(logits, dim=-1).squeeze()
    # class 1 = match
    return float(probs[1])


if __name__ == "__main__":
    p = match_probability("AXA XL Reinsurance Ltd", "AXA XL Re")
    print("Match probability:", p)