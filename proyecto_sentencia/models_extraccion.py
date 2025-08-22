import json
import os
from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
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
    resumen: str = Field(..., max_length=200, description="Resumen breve del punto de análisis.")
    pagina: int = Field(..., description="Número de página donde se encuentra la cita principal.")
    citas: List[Cita] = Field(..., min_items=0, max_items=5, description="Lista de citas textuales que soportan el punto.")

    @field_validator('citas', mode='before')
    @classmethod
    def partir_citas_largas(cls, v):
        """Parte citas largas en múltiples fragmentos preservando texto completo"""
        citas_procesadas = []
        
        for cita in v:
            texto_original = cita if isinstance(cita, str) else cita.get('texto', '')
            
            if len(texto_original) <= 500:
                # Cita normal, solo convertir a objeto
                citas_procesadas.append(Cita(texto=texto_original))
            else:
                # Cita larga: partir en chunks de palabras completas
                chunks = cls._partir_en_chunks(texto_original, max_chars=450)
                for chunk in chunks:
                    citas_procesadas.append(Cita(texto=chunk))
        
        return citas_procesadas

    @staticmethod
    def _partir_en_chunks(texto: str, max_chars: int = 450) -> List[str]:
        """Parte texto en chunks de palabras completas"""
        if len(texto) <= max_chars:
            return [texto]
        
        chunks = []
        palabras = texto.split()
        chunk_actual = ""
        
        for palabra in palabras:
            nuevo_chunk = chunk_actual + " " + palabra if chunk_actual else palabra
            
            if len(nuevo_chunk) <= max_chars:
                chunk_actual = nuevo_chunk
            else:
                if chunk_actual:
                    chunks.append(chunk_actual)
                    chunk_actual = palabra
                else:
                    chunks.append(palabra[:max_chars])
                    chunk_actual = ""
        
        if chunk_actual:
            chunks.append(chunk_actual)
        
        return chunks

    @field_validator('resumen', mode='before')
    @classmethod
    def truncar_resumen(cls, v):
        """Auto-trunca resumen si excede límite"""
        if len(v) <= 200:
            return v
        # Truncar en palabra completa
        palabras = v[:197].rsplit(' ', 1)
        return palabras[0] + "..." if len(palabras) > 1 else v[:197] + "..."

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
    puntos_analisis: List[PuntoAnalisis] = Field(..., min_items=0)
    decision_o_resolutivos: DecisionResolutivos
    normas_invocadas: List[str] = Field(..., description="Lista de artículos, leyes o tesis más relevantes mencionados.")
    metadatos_ubicacion: MetadatosUbicacion

    @field_validator('planteamiento_acto_reclamado', mode='before')  
    @classmethod
    def truncar_planteamiento(cls, v):
        """Auto-trunca planteamiento si excede límite"""
        if len(v) <= 280:
            return v
        palabras = v[:277].rsplit(' ', 1)
        return palabras[0] + "..." if len(palabras) > 1 else v[:277] + "..."