# processors/pdf_processor.py
"""
Procesador para archivos PDF
"""

import base64
from pathlib import Path
from typing import Tuple

class PDFProcessor:
    def extraer_contenido(self, ruta_archivo: Path) -> Tuple[str, str]:
        """
        Extrae contenido de un archivo PDF
        
        Returns:
            Tuple[str, str]: (contenido_base64, tipo_contenido)
        """
        with open(ruta_archivo, 'rb') as f:
            contenido_bytes = f.read()
        
        contenido_base64 = base64.b64encode(contenido_bytes).decode('utf-8')
        return contenido_base64, "pdf"