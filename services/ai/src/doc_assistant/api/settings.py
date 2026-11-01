from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiSettings:
    data_dir: Path
    upload_pdf_max_bytes: int
    upload_pdf_max_pages: int
    upload_image_max_bytes: int
