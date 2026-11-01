from dataclasses import dataclass, field

AMOUNT_COLS = {
    "base_imponible_total": "base_c",
    "cuota_iva_total": "iva_c",
    "irpf_importe": "irpf_c",
    "recargo_total": "recargo_c",
    "importe_total": "total_c",
    "irpf_tipo": "irpf_tipo_c",
}
DATE_COLS = {"fecha_emision": "fecha_emision_iso", "fecha_vencimiento": "fecha_vencimiento_iso"}


@dataclass
class Party:
    """One real-world party: same NIF, or same folded name when there is no NIF."""

    key: str
    nombre: str
    nif: str
    roles: dict[str, set[str]] = field(default_factory=dict)  # rol -> numeros
    matched: int = 0
    exact: int = 0
    score: float = 0.0
    full: bool = False

    def numeros(self, rol: str | None) -> set[str]:
        if rol:
            return set(self.roles.get(rol, set()))
        return set().union(*self.roles.values()) if self.roles else set()
