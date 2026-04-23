canonical = [
    "AXA XL",
    "Munich Re",
    "Swiss Re",
    "Allianz SE",
    "Hannover Re",
    "SCOR SE",
]
import random

def generate_variants(name):
    variants = []

    # Add legal suffixes
    suffixes = [" Ltd", " Limited", " SA", " AG", " PLC", " S.A.", " GmbH"]
    variants.append(name + random.choice(suffixes))

    # Add reinsurance boilerplate
    boiler = [" Reinsurance", " Reinsurance Company", " Re", " Re."]
    variants.append(name + random.choice(boiler))

    # Add country suffix
    countries = [" UK Branch", " Europe SA", " Asia", " US"]
    variants.append(name + random.choice(countries))

    # Add punctuation noise
    variants.append(name.replace(" ", "-"))
    variants.append(name.replace(" ", ""))

    return list(set(variants))

def build_positive_pairs(canonical_names):
    pairs = []
    for name in canonical_names:
        variants = generate_variants(name)
        for v1 in variants:
            for v2 in variants:
                if v1 != v2:
                    pairs.append((v1, v2, 1))
    return pairs

def build_hard_negatives(canonical_names):
    pairs = []
    for i in range(len(canonical_names)):
        for j in range(i+1, len(canonical_names)):
            a = canonical_names[i]
            b = canonical_names[j]

            # Make them deceptively similar
            variants_a = generate_variants(a)
            variants_b = generate_variants(b)

            for va in variants_a:
                for vb in variants_b:
                    if va.split()[0] == vb.split()[0]:  # same first token
                        pairs.append((va, vb, 0))
    return pairs

def build_random_negatives(canonical_names, count=2000):
    pairs = []
    for _ in range(count):
        a, b = random.sample(canonical_names, 2)
        pairs.append((random.choice(generate_variants(a)),
                      random.choice(generate_variants(b)),
                      0))
    return pairs

import pandas as pd

def build_dataset(canonical):
    pos = build_positive_pairs(canonical)
    hard = build_hard_negatives(canonical)
    rand = build_random_negatives(canonical)

    df = pd.DataFrame(pos + hard + rand, columns=["name_a", "name_b", "label"])
    df = df.sample(frac=1).reset_index(drop=True)
    df.to_csv("generated_training_data.csv", index=False)
    return df

df = build_dataset(canonical)
print(df.head())