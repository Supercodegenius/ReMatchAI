import faiss
import numpy as np
from your_embedding_module import embed  # Replace 'your_embedding_module' with the actual module name

# Suppose you have a list of all known reinsurer names
names = open("all_names.txt").read().splitlines()

embs = np.array([embed(n) for n in names]).astype("float32")

index = faiss.IndexFlatIP(embs.shape[1])  # cosine similarity
index.add(embs)

faiss.write_index(index, "reinsurance_index.faiss")

index = faiss.read_index("reinsurance_index.faiss")

query_emb = embed("AXA XL Re")
D, I = index.search(np.array([query_emb]).astype("float32"), k=5)

for score, idx in zip(D[0], I[0]):
    print(score, names[idx])
