"""
Modelos Pydantic para validación de estructura de documentos SCJN
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import json

class Cita(BaseModel):
    texto: str = Field(..., max_length=500, description="Fragmento textual literal")

class PuntoAnalisis(BaseModel):
    titulo: str = Field(..., max_length=100, description="Máx. 10 palabras")
    resumen: str = Field(..., max_length=120, description="Máx. 120 caracteres") 
    pagina: int = Field(..., ge=1, description="Número de página")
    citas: List[Cita] = Field(..., min_items=1, max_items=3)

class SCJN_Documento(BaseModel):
    documento: str = Field(..., description="Nombre exacto del archivo")
    tipo: str = Field(..., description="Ej. Acuerdo de Admisión, Demanda de Amparo")
    fecha_expedicion: str = Field(..., description="Fecha en formato YYYY-MM-DD")
    organo_emisor: str
    expediente: str
    folios: Optional[int] = Field(None, ge=1)
    paginas_pdf: List[int] = Field(..., min_items=2, max_items=2)
    
    partes: Dict[str, Any] = Field(..., description="Partes del proceso")
    planteamiento: str = Field(..., max_length=280)
    
    puntos_analisis: List[PuntoAnalisis] = Field(..., min_items=1)
    normas_invocadas: List[str] = Field(default_factory=list)
    pretensiones: List[str] = Field(..., min_items=1)
    
    # Metadatos opcionales
    url_boletin: Optional[str] = None
    tags: Optional[List[str]] = None

    @validator('paginas_pdf')
    def validar_paginas(cls, v):
        if len(v) == 2 and v[0] <= v[1]:
            return v
        raise ValueError('paginas_pdf debe ser [inicio, fin] donde inicio <= fin')

class DocumentoMetadata(BaseModel):
    """Metadata del documento original"""
    nombre_archivo: str
    formato: str
    tamano_bytes: int
    fecha_procesamiento: datetime
    hash_archivo: Optional[str] = None
    tokens_utilizados: Optional[int] = None
    tiempo_procesamiento: Optional[float] = None

class ExpedienteInfo(BaseModel):
    """Información del expediente completo"""
    numero_expediente: str
    fecha_inicio: datetime
    documentos_procesados: List[str]
    total_documentos: int
    tokens_totales: int
    tiempo_total_procesamiento: float

class BitacoraEntry(BaseModel):
    """Entrada de bitácora de procesamiento"""
    timestamp: datetime
    expediente: str
    documento: str
    status: str  # 'success', 'error', 'warning'
    mensaje: str
    metadata: DocumentoMetadata
    error_detalle: Optional[str] = None

class ReporteEjecutivo(BaseModel):
    """Estructura del reporte ejecutivo generado"""
    expediente: str
    fecha_generacion: datetime
    documentos_analizados: List[str]
    contenido_markdown: str
    tokens_utilizados: int
    tiempo_generacion: float