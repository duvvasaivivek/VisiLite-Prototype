import re
from dataclasses import dataclass
from app.models.schemas import Sensitivity

@dataclass
class Finding:
    entity_type: str
    match_string: str
    sensitivity: Sensitivity

PATTERNS = [
    ("CREDIT_CARD", r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"),
    ("SSN", r"\b\d{3}-\d{2}-\d{4}\b"),
    ("AADHAAR", r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b"),
    ("PAN", r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    ("IFSC", r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    ("CRYPTO_WALLET", r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b|\b0x[a-fA-F0-9]{40}\b"),
    ("PASSPORT", r"\b[A-Z][1-9]\d{6}[1-9]\b"),
    ("VOTER_ID", r"\b[A-Z]{3}\d{7}\b"),
    ("DL", r"\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{7}\b"),
    ("EMAIL", r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    ("UPI", r"\b[a-zA-Z0-9.\-_]{3,}@(?:okicici|oksbi|okhdfcbank|okaxis|okboi|ybl|upi|paytm|gpay|ibl|axl|sbi|icici|hdfc|apl|allbank|axisbank)\b"),
    ("IP", r"\b(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"),
]

CANDIDATE_PATTERNS = [
    ("NUMBER_CANDIDATE", r"\b(?:\+?1[-. ]?)?\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b|\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b|\b\d{9,18}\b"),
    ("DATE_CANDIDATE", r"\b(?:0[1-9]|[12]\d|3[01])[\/\-](?:0[1-9]|1[0-2])[\/\-](?:19|20)\d{2}\b"),
]

def resolve_candidate(match_string: str, candidate_type: str, text_before: str, context_str: str) -> str | None:
    combined = f"{text_before} {context_str}".lower()
    
    if candidate_type == "NUMBER_CANDIDATE":
        if re.search(r"\b(order|invoice|tracking|txn|transaction|id|no\.|number|ref|receipt|item|part|qty|quantity)\b", combined):
            return None
        if re.search(r"\b(phone|mobile|tel|cell|call|contact|sms|whatsapp|ph)\b", combined):
            return "PHONE"
        if re.search(r"\b(account|acct|bank|routing|ifsc|deposit|transfer)\b", combined):
            return "BANK_ACCOUNT"
            
        if re.search(r"\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}", match_string) and re.search(r"[-()]", match_string):
            return "PHONE"
        if re.search(r"\+?91", match_string):
            return "PHONE"
            
        return None
        
    if candidate_type == "DATE_CANDIDATE":
        if re.search(r"\b(dob|birth|born|age)\b", combined):
            return "DOB"
        return None
        
    return None

def detect_hybrid(text: str, context_str: str = "", input_type: str = "") -> list[Finding]:
    findings = []
    
    if input_type == "password" and text.strip():
        findings.append(Finding("PASSWORD", text, Sensitivity.SECRET))
        return findings
    
    for name, pattern in PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append(Finding(name, match.group(0), Sensitivity.HIGHLY_SENSITIVE))
            
    for name, pattern in CANDIDATE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 40)
            text_before = text[start:match.start()]
            resolved = resolve_candidate(match.group(0), name, text_before, context_str)
            if resolved:
                if "otp" in context_str.lower() or "otp" in text_before.lower():
                    findings.append(Finding(resolved, match.group(0), Sensitivity.SECRET))
                else:
                    findings.append(Finding(resolved, match.group(0), Sensitivity.HIGHLY_SENSITIVE))
                
    # Extra check for OTP that is just digits but context says OTP
    if "otp" in context_str.lower() or "otp" in text.lower():
        # simple 4-8 digit OTP
        for match in re.finditer(r"\b\d{4,8}\b", text):
            # check context again
            start = max(0, match.start() - 40)
            if "otp" in text[start:match.start()].lower() or "otp" in context_str.lower():
                findings.append(Finding("OTP", match.group(0), Sensitivity.SECRET))

    return findings
