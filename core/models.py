from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

def partir_cita_larga(cita_texto: str, max_chars: int = 950) -> List[str]:
    """
    Parte citas largas en fragmentos de palabras completas
    
    Args:
        cita_texto: Texto de la cita original
        max_chars: Máximo de caracteres por fragmento (default 950 para dejar margen)
    
    Returns:
        Lista de fragmentos de máximo 5 elementos
    """
    if len(cita_texto) <= max_chars:
        return [cita_texto]
    
    fragmentos = []
    palabras = cita_texto.split()
    fragmento_actual = ""
    
    for palabra in palabras:
        # Verificar si agregar la siguiente palabra excede el límite
        nuevo_fragmento = fragmento_actual + " " + palabra if fragmento_actual else palabra
        
        if len(nuevo_fragmento) <= max_chars:
            fragmento_actual = nuevo_fragmento
        else:
            # Guardar fragmento actual si existe
            if fragmento_actual:
                fragmentos.append(fragmento_actual)
                fragmento_actual = palabra
            else:
                # Caso edge: palabra individual muy larga
                fragmentos.append(palabra[:max_chars])
                fragmento_actual = ""
    
    # Agregar último fragmento si existe
    if fragmento_actual:
        fragmentos.append(fragmento_actual)
    
    # Máximo 5 fragmentos como solicitaste
    return fragmentos[:5]


class Cita(BaseModel):
    texto: str = Field(..., max_length=1000, description="Fragmento textual literal")

class PuntoAnalisis(BaseModel):
    titulo: str = Field(..., max_length=200, description="Máx. 30 palabras")
    resumen: str = Field(..., max_length=200, description="Máx. 200 caracteres") 
    pagina: int = Field(..., ge=1, description="Número de página")
    citas: List[Union[Cita, str]] = Field(..., min_items=1, max_items=5)
    
    @field_validator('citas', mode='before')
    @classmethod
    def normalize_citas(cls, v):
        """Convierte strings a objetos Cita y maneja citas largas automáticamente"""
        normalized = []
        
        for cita in v:
            if isinstance(cita, str):
                # Si la cita es muy larga, partirla automáticamente
                fragmentos = partir_cita_larga(cita)
                
                # Crear objeto Cita para cada fragmento
                for fragmento in fragmentos:
                    normalized.append(Cita(texto=fragmento))
                    
            elif isinstance(cita, dict) and 'texto' in cita:
                # Si es dict, verificar también si es muy largo
                texto_original = cita['texto']
                fragmentos = partir_cita_larga(texto_original)
                
                for fragmento in fragmentos:
                    normalized.append(Cita(texto=fragmento))
            else:
                # Ya es objeto Cita, verificar longitud
                if hasattr(cita, 'texto'):
                    fragmentos = partir_cita_larga(cita.texto)
                    for fragmento in fragmentos:
                        normalized.append(Cita(texto=fragmento))
                else:
                    normalized.append(cita)
        
        return normalized

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

    @field_validator('paginas_pdf')
    @classmethod
    def validar_paginas(cls, v):
        if len(v) == 2 and v[0] <= v[1]:
            return v
        raise ValueError('paginas_pdf debe ser [inicio, fin] donde inicio <= fin')

# Resto de las clases igual...
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