# processors/txt_processor.py
"""
Procesador para archivos de texto plano
"""

from pathlib import Path
from typing import Tuple
import chardet

class TXTProcessor:
    def extraer_contenido(self, ruta_archivo: Path) -> Tuple[str, str]:
        """
        Extrae contenido de un archivo de texto
        
        Returns:
            Tuple[str, str]: (contenido_texto, tipo_contenido)
        """
        try:
            # Detectar encoding
            with open(ruta_archivo, 'rb') as f:
                raw_data = f.read()
            
            encoding_info = chardet.detect(raw_data)
            encoding = encoding_info.get('encoding', 'utf-8')
            
            # Leer archivo con encoding detectado
            with open(ruta_archivo, 'r', encoding=encoding) as f:
                contenido = f.read()
            
            return contenido, "text"
            
        except Exception as e:
            # Fallback a utf-8
            try:
                with open(ruta_archivo, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                return contenido, "text"
            except:
                raise Exception(f"Error procesando archivo de texto: {str(e)}")