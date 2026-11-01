from pathlib import Path
from doc_assistant.domain.documents.chunking import ws
from doc_assistant.infra.pdf.extract import chunk_pdf, extract_pdf_text

root = Path('evidence/fixtures/docs')
cases = {
    'robot-demo.pdf': ['Desconectar la alimentacion antes del mantenimiento.', 'Tension nominal: 24 V.', 'Carga maxima: 12 kg.'],
    'sensor-demo.pdf': ['Montar sobre una superficie plana con tornillos M4.', 'Alcance: 4 m.', 'Temperatura de trabajo: 0 a 50 C.'],
}
for name, facts in cases.items():
    path = root / name
    section = [c['body'] for c in chunk_pdf(path)]
    text = ws(' '.join(page['text'] for page in extract_pdf_text(path)))
    fixed = [text[i:i + 64] for i in range(0, len(text), 64)]
    for label, chunks in [('secciones', section), ('fijo-64', fixed)]:
        intact = sum(any(fact in c for c in chunks) for fact in facts)
        print(f'{name} {label}: fragmentos={len(chunks)} hechos_integros={intact}/{len(facts)} caracteres={sum(map(len, chunks))}')
