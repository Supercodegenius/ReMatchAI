"""Treaty summariser: local Llama (via Ollama) with a rule-based fallback."""
from __future__ import annotations

import io
import json
import os
import re
import urllib.request

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
MAX_CHARS = 24000

FIELDS = {
    "cedant": "Name of the ceding company",
    "reinsurer": "Reinsurer or reinsurers and their shares",
    "class_of_business": "Class or line of business covered",
    "treaty_type": "Treaty type, e.g. quota share, excess of loss, stop loss",
    "period": "Inception and expiry dates",
    "territory": "Territorial scope",
    "limit": "Limit of liability, with currency",
    "retention": "Retention or deductible",
    "premium_or_rate": "Premium, rate or rate on line",
    "commission": "Ceding or profit commission",
    "reinstatements": "Reinstatement terms",
    "exclusions": "Main exclusions",
    "key_clauses": "Notable clauses, e.g. loss triggers, termination, claims control, sunset, arbitration",
}

_FALLBACK = {
    "limit": r"(?:limit(?: of liability)?|each and every loss|excess of)[^.\n]{0,80}?((?:USD|US\$|\$|EUR|GBP)\s?[\d,\.]+\s?(?:m|million|bn)?)",
    "retention": r"(?:retention|deductible|attachment|in excess of)[^.\n]{0,60}?((?:USD|US\$|\$|EUR|GBP)\s?[\d,\.]+\s?(?:m|million)?)",
    "commission": r"(?:commission)[^.\n]{0,60}?(\d{1,2}(?:\.\d+)?\s?%)",
    "premium_or_rate": r"(?:premium|rate on line|rol)[^.\n]{0,60}?((?:USD|US\$|\$|EUR|GBP)?\s?[\d,\.]+\s?(?:m|million|%)?)",
    "reinstatements": r"([^.\n]{0,40}reinstatements?[^.\n]{0,80})",
    "period": r"((?:period|inception|effective)[^.\n]{0,100})",
    "territory": r"(territor(?:y|ial)[^.\n]{0,100})",
    "exclusions": r"(exclusions?[^.\n]{0,160})",
    "treaty_type": r"(quota share|surplus|excess of loss|stop loss|per risk|catastrophe)",
    "cedant": r"(?:cedant|company|reassured)[:\s]+([A-Z][^\n,.]{2,60})",
}


def extract_text(name: str, data: bytes) -> str:
    n = name.lower()
    if n.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    if n.endswith(".docx"):
        from docx import Document
        return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    return data.decode("utf-8", errors="ignore")


def _prompt(text: str) -> str:
    spec = "\n".join(f'- "{k}": {v}' for k, v in FIELDS.items())
    return ("You are a reinsurance contracts analyst. Read the treaty below and reply with ONLY a JSON object with "
            "these keys (use \"Not stated\" if absent; never invent figures):\n" + spec +
            ',\n- "summary": a plain-English summary of 4-6 sentences for an underwriter'
            ',\n- "red_flags": a list of short strings for unusual, onerous or missing terms\n\nTREATY:\n' + text[:MAX_CHARS])


def ollama_available(host: str = OLLAMA_HOST) -> bool:
    try:
        urllib.request.urlopen(host + "/api/tags", timeout=2)
        return True
    except Exception:
        return False


def summarise_llm(text: str, model: str = DEFAULT_MODEL, host: str = OLLAMA_HOST) -> dict:
    body = json.dumps({"model": model, "stream": False, "format": "json",
                       "options": {"temperature": 0},
                       "messages": [{"role": "user", "content": _prompt(text)}]}).encode()
    req = urllib.request.Request(host + "/api/chat", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        content = json.loads(r.read())["message"]["content"]
    out = json.loads(content)
    out["red_flags"] = [str(x) for x in out.get("red_flags") or []]
    return out


def summarise_rules(text: str) -> dict:
    out = {k: "Not stated" for k in FIELDS}
    for k, pat in _FALLBACK.items():
        m = re.search(pat, text, flags=re.I)
        if m:
            out[k] = re.sub(r"\s+", " ", m.group(1)).strip()
    flags = []
    if out["exclusions"] == "Not stated":
        flags.append("No exclusions clause found; check the wording manually.")
    if out["retention"] == "Not stated":
        flags.append("No retention found.")
    if re.search(r"unlimited|no limit", text, re.I):
        flags.append("Wording mentions unlimited cover.")
    out["summary"] = ("Rule-based extraction (no Llama available). Fields were found by keyword search, so "
                      "check them against the wording.")
    out["red_flags"] = flags
    return out


def summarise(text: str, model: str = DEFAULT_MODEL, host: str = OLLAMA_HOST) -> tuple[dict, str]:
    """Returns (result, engine) where engine is 'llama' or 'rules'."""
    if ollama_available(host):
        try:
            return summarise_llm(text, model, host), "llama"
        except Exception as exc:  # fall back rather than fail the page
            res = summarise_rules(text)
            res["red_flags"].insert(0, f"Llama call failed ({type(exc).__name__}); showing rule-based extraction.")
            return res, "rules"
    return summarise_rules(text), "rules"


SAMPLE = """QUOTA SHARE / EXCESS OF LOSS REINSURANCE TREATY
Cedant: XYZ Insurance Ltd. Class: Marine Cargo. Type: Excess of Loss.
Period: 1 January 2026 to 31 December 2026. Territory: Worldwide excluding USA.
Limit of liability: USD 25,000,000 each and every loss in excess of USD 5,000,000 retention.
Premium: USD 3,000,000 at a rate on line of 12%. Ceding commission 20%.
Reinstatements: one at 100% additional premium, pro rata as to amount only.
Exclusions: war, nuclear, cyber, and pollution other than sudden and accidental.
Claims control clause applies. Either party may terminate on 90 days notice.
"""
