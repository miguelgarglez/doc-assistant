"""Generate fictional technical PDFs reproducibly with ReportLab."""

from pathlib import Path

from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "docs"
DOCUMENTS = {
    "robot-demo.pdf": [
        "Manual del robot ficticio TX-10",
        "1. Seguridad",
        "Desconectar la alimentacion antes del mantenimiento.",
        "2. Especificaciones",
        "Tension nominal: 24 V. Carga maxima: 12 kg.",
    ],
    "sensor-demo.pdf": [
        "Ficha del sensor ficticio SX-20",
        "1. Instalacion",
        "Montar sobre una superficie plana con tornillos M4.",
        "2. Especificaciones",
        "Alcance: 4 m. Temperatura de trabajo: 0 a 50 C.",
    ],
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, lines in DOCUMENTS.items():
        pdf = canvas.Canvas(str(OUT / filename), invariant=1)
        for index, line in enumerate(lines):
            pdf.drawString(50, 800 - index * 24, line)
        pdf.save()


if __name__ == "__main__":
    main()
