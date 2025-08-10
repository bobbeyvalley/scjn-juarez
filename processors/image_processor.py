# processors/image_processor.py
"""
Procesador para archivos de imagen (OCR)
"""

import base64
from pathlib import Path
from typing import Tuple

class ImageProcessor:
    def extraer_contenido(self, ruta_archivo: Path) -> Tuple[str, str]:
        """
        Extrae contenido de un archivo de imagen
        
        Returns:
            Tuple[str, str]: (contenido_base64, tipo_contenido)
        """
        try:
            with open(ruta_archivo, 'rb') as f:
                contenido_bytes = f.read()
            
            contenido_base64 = base64.b64encode(contenido_bytes).decode('utf-8')
            return contenido_base64, "image"
            
        except Exception as e:
            raise Exception(f"Error procesando imagen: {str(e)}")