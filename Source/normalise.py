

LEGAL_SUFFIXES = [
    "ltd", "limited", "plc", "llc", "inc", "corp", "co", "company",
    "ag", "sa", "s.a.", "s.a", "spa", "gmbh", "bv", "nv", "oy", "ab",
    "pte", "pvt", "kg", "kgaa", "sas", "sarl", "llp", "lp"
]
REINSURANCE_TERMS = [
    "reinsurance", "reinsurance company", "reinsurance co",
    "re", "re.", "reins", "reins.", "reassurance",
    "underwriting", "insurance", "insurance company",
    "branch", "uk branch", "europe sa", "europe s.a."
]

import unicodedata
import re

TERMINAL_LEGAL_SUFFIX_VARIANTS = {
    "a g": "ag",
    "c o": "co",
    "b v": "bv",
    "c o m p a n y": "company",
    "g m b h": "gmbh",
    "k g": "kg",
    "k g a a": "kgaa",
    "l l c": "llc",
    "l l p": "llp",
    "l p": "lp",
    "l t d": "ltd",
    "n v": "nv",
    "o y": "oy",
    "p l c": "plc",
    "p t e": "pte",
    "p v t": "pvt",
    "s p z o o": "spzoo",
    "s a": "sa",
    "s a r l": "sarl",
    "s a s": "sas",
    "s p a": "spa",
}


def canonicalize_terminal_legal_suffix(s):
    normalized = str(s or "").strip()
    if not normalized:
        return ""

    for variant, canonical in TERMINAL_LEGAL_SUFFIX_VARIANTS.items():
        normalized = re.sub(rf"\b{variant}\b$", canonical, normalized)
    return normalized

def clean_text(s):
    s = s.lower().strip()
    s = re.sub(r"[\u2010-\u2015\u2212\u002d]", " ", s)  # replace hyphens/dashes with space before encoding
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return canonicalize_terminal_legal_suffix(s)

def remove_terms(s, terms):
    tokens = s.split()
    filtered = [t for t in tokens if t not in terms]
    return " ".join(filtered)

def normalise_name(name):
    s = clean_text(name)

    s = remove_terms(s, LEGAL_SUFFIXES)
    s = remove_terms(s, REINSURANCE_TERMS)

    # Remove standalone country codes
    COUNTRY_TERMS = ["uk", "usa", "us", "eu", "europa", "asia", "emea"]
    s = remove_terms(s, COUNTRY_TERMS)

    # Remove repeated spaces again
    s = " ".join(s.split())

    return s
