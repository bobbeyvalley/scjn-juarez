import json
import os
from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import logging

# --- DEFINICIÓN DEL CATÁLOGO DE ETAPAS (Enum) ---
# Esta es la "fuente única de la verdad" para las etapas procesales.
# Es un contrato que tanto el LLM como el código deben respetar.


class EtapaProcesalEnum(str, Enum):
    JUICIO_DE_ORIGEN = "Juicio de Origen"
    RECURSO_DE_APELACION = "Recurso de Apelación"
    DEMANDA_DE_AMPARO = "Demanda de Amparo"
    SENTENCIA_DE_AMPARO_DIRECTO = "Sentencia de Amparo Directo"
    RECURSO_DE_REVISION = "Recurso de Revisión"
    ACUERDO_ADMISION_REVISION = "Acuerdo de Admisión de Revisión"
    AVOCAMIENTO = "Avocamiento"
    # Se pueden agregar más etapas aquí, y el sistema las reconocerá.
    OTRA = "Otra" # Una opción de escape por si algo es verdaderamente ambiguo


# --- Modelos de Soporte ---

class Cita(BaseModel):
    """
    Representa un fragmento textual extraído de un documento.
    """
    texto: str = Field(..., max_length=500, description="Fragmento textual que respalda un punto de análisis.")

class PuntoAnalisis(BaseModel):
    """
    Representa un argumento clave, concepto de violación, agravio o punto resolutivo
    identificado en el documento.
    """
    titulo: str = Field(..., max_length=100, description="Título conciso del punto (guía: máx. 10 palabras).")
    resumen: str = Field(..., max_length=120, description="Resumen breve del punto de análisis.")
    pagina: int = Field(..., description="Número de página donde se encuentra la cita principal.")
    citas: List[Cita] = Field(..., min_items=1, max_items=3, description="Lista de citas textuales que soportan el punto.")

# --- Modelos Estructurales Jerárquicos ---

class IdentificacionBasica(BaseModel):
    """
    Contiene los datos de identificación fundamentales del documento y su contexto procesal.
    """
    tipo_documento: str = Field(..., description="Tipo de actuación (ej. 'Acuerdo de Admisión', 'Sentencia de Amparo Directo').")
    etapa_procesal_resuelta: EtapaProcesalEnum #str = Field(..., description="Etapa del juicio que este documento resuelve o inicia (ej. 'Recurso de Apelación').")
    fecha_resolucion: date = Field(..., description="Fecha en que se dictó la sentencia o acuerdo (formato AAAA-MM-DD). La conversión a texto se hace en post-procesamiento.")
    organo_emisor: str = Field(..., description="Tribunal, Sala o entidad que emite el documento.")
    expedientes_principales: List[str] = Field(..., description="Array de los números de expediente asignados a ESTA actuación.")
    folios: Optional[int] = Field(None, description="Número total de fojas o páginas del documento físico.")

class Partes(BaseModel):
    """
    Identifica a las partes involucradas en la etapa procesal correspondiente.
    """
    quejoso_recurrente: str = Field(..., description="Nombre de la persona o entidad quejosa o recurrente.")
    autoridad_responsable: str = Field(..., description="Nombre de la autoridad cuya resolución se impugna en ESTA etapa.")
    terceros_interesados: Optional[List[str]] = Field(None, description="Array con los nombres de los terceros interesados.")

class DecisionResolutivos(BaseModel):
    """
    Captura el resultado o la decisión final del documento analizado. Reemplaza al campo 'pretensiones'.
    """
    sentido_del_fallo: str = Field(..., description="Describe el resultado principal (ej. 'Se niega el amparo', 'Se admite el recurso').")
    puntos_resolutivos: List[str] = Field(..., description="Array con la transcripción literal de los puntos resolutivos o determinaciones principales.")

class MetadatosUbicacion(BaseModel):
    """
    Información sobre la ubicación del documento dentro de un archivo PDF más grande.
    """
    paginas_pdf: List[int] = Field(..., min_items=2, max_items=2, description="[página_inicio, página_fin] del documento en el PDF original.")

# --- Modelo Principal ---

class SCJNDocumentoMapeado(BaseModel):
    """
    Modelo principal para validar la estructura de datos extraída de un documento judicial,
    optimizado para la generación de antecedentes de un proyecto de sentencia de la SCJN.
    """
    documento: str = Field(..., description="Nombre exacto del archivo de origen.")
    
    # Secciones jerárquicas
    identificacion_basica: IdentificacionBasica
    partes: Partes
    planteamiento_acto_reclamado: str = Field(..., max_length=280, description="Resumen de la controversia principal o la decisión impugnada en este documento.")
    puntos_analisis: List[PuntoAnalisis] = Field(..., min_items=1)
    decision_o_resolutivos: DecisionResolutivos
    normas_invocadas: List[str] = Field(..., description="Lista de artículos, leyes o tesis más relevantes mencionados.")
    metadatos_ubicacion: MetadatosUbicacion