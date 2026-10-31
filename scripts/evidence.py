"""Regenera evidence/: capturas Playwright (sin modelos) y, con --live, una corrida
real con documentos y facturas sintéticos de evidence/fixtures (requiere modelos y,
para facturas, Ollama con glm-ocr). Salida: evidence/live/results.{json,md}.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _common import ROOT
from package import http_ok, port_busy

FIX = ROOT / "evidence" / "fixtures"
OUT = ROOT / "evidence" / "live"
WEB = "http://127.0.0.1:3000/api"
QUESTIONS = [
    ("documento", "¿Qué alcance tiene el sensor SX-20?"),
    ("documento", "¿Qué temperatura de trabajo admite el sensor?"),
    ("factura", "¿Cuál es el importe total de la factura F-2026-001?"),
    ("rechazo esperado", "¿Cuál es el precio del robot?"),
    ("rechazo esperado", "¿Quién ganó el mundial de 2010?"),
]


def multipart(path: Path, ctype: str) -> tuple[bytes, str]:
    b = uuid.uuid4().hex
    head = (
        f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode()
    return (
        head + path.read_bytes() + f"\r\n--{b}--\r\n".encode(),
        f"multipart/form-data; boundary={b}",
    )


def screenshots() -> None:
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        raise SystemExit("[evidence] necesito pnpm (mise install)")
    subprocess.run([pnpm, "--filter", "web", "e2e"], cwd=ROOT, check=True)
    print("[evidence] capturas en evidence/screenshots")


def live() -> None:
    busy = [p for p in (3000, 8000, 8081, 8082, 8083) if port_busy(p)]
    if busy:
        raise SystemExit(f"[evidence] puertos ocupados {busy}: cierra el stack")
    OUT.mkdir(parents=True, exist_ok=True)
    log = open(OUT / "start.log", "w")  # noqa: SIM115
    kw: dict[str, Any] = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}  # type: ignore[attr-defined]
        if sys.platform == "win32"
        else {"start_new_session": True}
    )
    p = subprocess.Popen([sys.executable, "scripts/dev.py"], cwd=ROOT, stdout=log, stderr=log, **kw)
    res: dict[str, Any] = {
        "fecha": time.strftime("%Y-%m-%d %H:%M %Z"),
        "documentos": [],
        "facturas": [],
        "preguntas": [],
    }
    try:
        t_end = time.time() + 300
        while True:
            try:
                http_ok(f"{WEB}/health")
                break
            except OSError:
                if p.poll() is not None or time.time() > t_end:
                    raise SystemExit(
                        "[evidence] el stack no arrancó; ver evidence/live/start.log"
                    ) from None
                time.sleep(2)
        for pdf in sorted((FIX / "docs").glob("*.pdf")):
            body, ct = multipart(pdf, "application/pdf")
            r = json.loads(http_ok(f"{WEB}/documents", body, ct))
            res["documentos"].append({"fichero": pdf.name, "n_chunks": r["n_chunks"]})
        for img in sorted((FIX / "invoices").glob("*.png")):
            gt = json.loads(img.with_suffix(".json").read_text())["ground_truth"]
            body, ct = multipart(img, "image/png")
            t0 = time.time()
            try:
                r = json.loads(http_ok(f"{WEB}/invoices/upload", body, ct))
            except OSError as e:
                res["facturas"].append({"fichero": img.name, "error": str(e)})
                continue
            rec = r["record"]
            pairs = {
                "numero": "invoice_number",
                "base_imponible_total": "subtotal",
                "cuota_iva_total": "vat_total",
                "irpf_importe": "irpf_amount",
                "importe_total": "total",
            }
            diff = {
                k: [rec.get(k), gt[v]] for k, v in pairs.items() if str(rec.get(k)) != str(gt[v])
            }
            res["facturas"].append(
                {
                    "fichero": img.name,
                    "estado": r["estado"],
                    "motivo": r["motivo"],
                    "discrepancias": diff,
                    "segundos": round(time.time() - t0, 1),
                }
            )
        for kind, q in QUESTIONS:
            t0 = time.time()
            r = json.loads(http_ok(f"{WEB}/ask", json.dumps({"question": q}).encode()))
            res["preguntas"].append(
                {
                    "tipo": kind,
                    "pregunta": q,
                    "ok": r["ok"],
                    "respuesta": r["answer"],
                    "motivo": r["reason"],
                    "citas": [(c["doc"], c["pages"], c["quote"]) for c in r["citations"]],
                    "segundos": round(time.time() - t0, 1),
                }
            )
    finally:
        if sys.platform == "win32":
            p.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        else:
            os.killpg(p.pid, signal.SIGINT)
        p.wait(timeout=30)
        log.close()
    (OUT / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    md = [
        f"# Corrida real con datos sintéticos — {res['fecha']}",
        "",
        "Generado por `mise run evidence --live`. Datos: evidence/fixtures (sintéticos). No es la evaluación final.",
        "",
        "## Facturas",
        "",
        "| fichero | estado | discrepancias | s |",
        "|---|---|---|---|",
    ]
    md += [
        f"| {f['fichero']} | {f.get('estado', 'error')} | {f.get('discrepancias', f.get('error'))} | {f.get('segundos', '')} |"
        for f in res["facturas"]
    ]
    md += [
        "",
        "## Preguntas",
        "",
        "| tipo | pregunta | ok | respuesta / motivo | citas | s |",
        "|---|---|---|---|---|---|",
    ]
    md += [
        f"| {q['tipo']} | {q['pregunta']} | {q['ok']} | {q['respuesta'] if q['ok'] else q['motivo']} | {'; '.join(f'{d} p.{pg}' for d, pg, _ in q['citas'])} | {q['segundos']} |"
        for q in res["preguntas"]
    ]
    (OUT / "results.md").write_text("\n".join(md) + "\n")
    print("[evidence] evidence/live/results.md")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true", help="además, corrida real con modelos")
    ap.add_argument("--no-screenshots", action="store_true")
    a = ap.parse_args()
    if not a.no_screenshots:
        screenshots()
    if a.live:
        live()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
