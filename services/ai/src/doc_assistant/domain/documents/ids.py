import hashlib


def pdf_doc_id(name: str) -> str:
    return "pdf-" + hashlib.sha256(name.encode()).hexdigest()[:12]


def invoice_doc_id(number: str) -> str:
    return "inv-" + hashlib.sha256(number.encode()).hexdigest()[:12]


def chunk_id_for(doc: str, section: str, body: str) -> str:
    return hashlib.sha1(f"{doc}|{section}|{body}".encode()).hexdigest()[:12]
