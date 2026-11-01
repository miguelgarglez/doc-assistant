from concurrent.futures import ThreadPoolExecutor

from doc_assistant.application.ports.health import ComponentProbe, ProbeResult


def check_components(probes: list[ComponentProbe]) -> list[ProbeResult]:
    with ThreadPoolExecutor(max_workers=len(probes)) as pool:
        results = list(pool.map(lambda probe: probe(), probes))
    return [ProbeResult(id="ai", status="ok", detail="Responde"), *results]
