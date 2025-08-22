import json
import os
from datetime import datetime
import logging
from .models_extraccion import SCJNDocumentoMapeado

# Configurar un logger simple para ver las advertencias
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def crear_contexto_del_caso_robusto(lista_archivos_json: list, id_caso: str, output_dir: str = '.') -> dict:
    """
    Versión robusta que lee, ordena y consolida los JSONs de un caso,
    manejando etapas no definidas y registrando advertencias.
    """
    ORDEN_ETAPAS = {
        "Juicio de Origen": 1,
        "Recurso de Apelación": 2,
        "Demanda de Amparo": 3,
        "Sentencia de Amparo Directo": 4,
        "Recurso de Revisión": 5,
        "Acuerdo de Admisión de Revisión": 6,
        "Avocamiento": 7
    }

    hitos_procesales = []
    for archivo_path in lista_archivos_json:
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                hitos_procesales.append(data)
        except Exception as e:
            logging.error(f"No se pudo procesar el archivo {archivo_path}. Error: {e}")
            continue

    def clave_ordenamiento(documento):
        etapa = documento.get('identificacion_basica', {}).get('etapa_procesal_resuelta', 'ETAPA_DESCONOCIDA')
        fecha_str = documento.get('identificacion_basica', {}).get('fecha_resolucion', '1900-01-01')
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        
        orden = ORDEN_ETAPAS.get(etapa)
        if orden is None:
            # ¡Aquí está la mejora! Si no conoce la etapa, la loguea y le da prioridad baja.
            logging.warning(f"Etapa no definida en ORDEN_ETAPAS: '{etapa}'. Se enviará al final de la cronología.")
            orden = 99  # Prioridad por defecto para etapas desconocidas
            
        return (orden, fecha)

    hitos_procesales.sort(key=clave_ordenamiento)

    expediente_principal = "No identificado"
    if hitos_procesales:
        expediente_principal = hitos_procesales[-1].get('identificacion_basica', {}).get('expedientes_principales', ["No identificado"])[0]

    contexto_final = {
        "metadata_caso": {
            "id_caso": id_caso,
            "expediente_principal": expediente_principal,
            "fecha_orquestacion": datetime.now().isoformat()
        },
        "hitos_procesales": hitos_procesales
    }

    output_filename = os.path.join(output_dir, f"CONTEXTO_{id_caso}.json")
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(contexto_final, f, ensure_ascii=False, indent=2)
    
    logging.info(f"Orquestador del caso guardado en: {output_filename}")
    return contexto_final

# --- Ejemplo de Uso ---
if __name__ == '__main__':
    # ... (el mismo ejemplo de uso que antes)
    pass