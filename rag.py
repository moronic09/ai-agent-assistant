from pypdf import PdfReader

DOCS = []

def load_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"
    return text

def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+chunk_size])
        i += chunk_size - overlap
    return chunks

def store_document(file):
    text = load_pdf(file)
    if not text.strip():
        return
    chunks = chunk_text(text)
    DOCS.extend(chunks)

def retrieve(query, k=3):
    q_words = set(query.lower().split())

    scored = []
    for c in DOCS:
        c_words = set(c.lower().split())
        score = len(q_words & c_words)
        scored.append((score, c))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [c for s, c in scored[:k] if s > 0] or DOCS[:k]