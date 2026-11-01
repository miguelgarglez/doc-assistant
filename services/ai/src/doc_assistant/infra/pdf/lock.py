"""Serialize PDFium calls, including creation and destruction of its objects."""

from threading import RLock

pdf_lock = RLock()
