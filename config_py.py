"""
Configuración del Sistema de Análisis Jurisprudencial SCJN
"""

import os
from typing import Dict, List

class Config:
    """Configuración general del sistema"""
    
    # API Keys
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    
    # Configuración de Gemini
    GEMINI_MODEL = "gemini-2.5-flash"
    GEMINI_TEMPERATURE = 0
    GEMINI_THINKING_BUDGET = 0
    
    # Extensiones de archivo soportadas
    EXTENSIONES_SOPORTADAS = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.txt': 'text/plain',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff'
    }
    
    # Configuración de procesamiento
    TIMEOUT_BASE_SEGUNDOS = 120
    MAX_REINTENTOS = 2
    PAUSA_ENTRE_REINTENTOS_SEGUNDOS = 5
    PAUSA_ENTRE_DOCUMENTOS_SEGUNDOS = 2.0
    
    # Directorios de salida dentro del expediente
    CARPETA_JSONS = "jsons"
    CARPETA_REPORTE = "reporte"
    
    # Nombres de archivos
    NOMBRE_BITACORA = "bitacora_proceso.json"
    SUFIJO_JSON_MAPEADO = "_mapeado.json"
    PREFIJO_REPORTE = "reporte_ejecutivo_"
    
    # Límites y validaciones
    MAX_LONGITUD_TITULO_PUNTO = 100
    MAX_LONGITUD_RESUMEN_PUNTO = 120
    MAX_LONGITUD_PLANTEAMIENTO = 280
    MAX_LONGITUD_CITA = 500
    MIN_PUNTOS_ANALISIS = 1
    MAX_CITAS_POR_PUNTO = 3
    
    # Estimación de costos (USD por token - aproximado)
    COSTO_ESTIMADO_POR_TOKEN = 0.000001
    
    @classmethod
    def validar_configuracion(cls):
        """Valida que la configuración esté completa"""
        errores = []
        
        if not cls.GEMINI_API_KEY:
            errores.append("GEMINI_API_KEY no está configurada en las variables de entorno")
        
        if errores:
            raise ValueError("Errores de configuración:\n" + "\n".join(f"- {error}" for error in errores))
        
        return True
    
    @classmethod
    def get_configuracion_procesamiento(cls) -> Dict:
        """Retorna configuración para el procesamiento de documentos"""
        return {
            'timeout_base_segundos': cls.TIMEOUT_BASE_SEGUNDOS,
            'max_reintentos': cls.MAX_REINTENTOS,
            'pausa_entre_reintentos_segundos': cls.PAUSA_ENTRE_REINTENTOS_SEGUNDOS,
            'pausa_entre_documentos_segundos': cls.PAUSA_ENTRE_DOCUMENTOS_SEGUNDOS
        }


class PromptTemplates:
    """Templates de prompts para Gemini"""
    
    MAPEO_PROMPT = """Actúa como experto en análisis documental y legal desde la perspectiva del marco constitucional y regulatorio de México y analiza la siguiente información para poder identificar información relevante de los siguientes documentos que permitan identificar la competencia, legitimidad y procedencia de la intervención de la suprema corte de justicia en la resolución de este asunto.
Sólo responde con el objeto JSON, no des explicaciones. La respuesta es en Español Mexicano
A partir del documento que se te proporcione genera un objeto json con las siguientes llaves:

Nombre del documento
Incluye exactamente el nombre del archivo (campo "documento").
Identificación básica
Extrae: tipo de documento, fecha de expedición, órgano emisor, expediente(s) citados y número de fojas o páginas.
Partes relevantes
Quejoso / promovente / recurrente
Autoridad responsable
Terceros interesados (si los hay)
Planteamiento o acto reclamado
Frase breve (≤ 280 caracteres) que resuma la controversia o decisión impugnada.
Puntos de análisis (array)
Para cada punto:
"titulo": máx. 10 palabras
"resumen": máx. 120 caracteres
"pagina": página(s) exacta(s) dentro del PDF
"citas": 1-3 fragmentos textuales literalmente copiados (≤ 500 caracteres c/u) que respalden el punto.
Normas o precedentes invocados
Lista breve de artículos constitucionales, leyes o tesis jurisprudenciales mencionados, sólo mencionados a un nivel general sin extraer el detalle de cada documento citado.
Pretensiones o resolución
Array con cada petición o determinación final.
Metadatos de ubicación
"paginas_pdf": [inicio, fin] del documento en el PDF original.
Profundidad
Conserva jerarquía: "conceptos_violacion" o "acuerdos" como sub-arrays cuando aplique.

Ejemplo de salida esperada (solo ilustrativo):
{
  "documento": "ADMISIÓN ADR 1241 2024.pdf",
  "tipo": "Acuerdo de Admisión",
  "fecha_expedicion": "2024-02-12",
  "organo_emisor": "Presidencia de la SCJN",
  "expediente": "1241/2024",
  "folios": 11,
  "paginas_pdf": [1, 11],
  "partes": {
    "quejoso": "Corporativo Ferloguer, S.A. de C.V.",
    "autoridad_responsable": "6ª Sala Civil TSJCDMX"
  },
  "planteamiento": "Consecuencias civiles de la falsedad en la promesa de decir verdad.",
  "puntos_analisis": [
    {
      "titulo": "Interpretación art. 130",
      "resumen": "Solicita aclarar efectos civiles de la promesa incumplida.",
      "pagina": 3,
      "citas": [
        "¿puede acaso hacer y tres manifestaciones diversas… y pretender que todas sean válidas?"
        ]
    }
  ],
  "normas_invocadas": ["Art. 130 CPEUM", "Art. 107 fracc. IX CPEUM"],
  "pretensiones": ["Admitir el recurso de revisión"]
}"""

    REPORTE_PROMPT = """**PROMPT PARA GENERACIÓN DE REPORTE EJECUTIVO DE CASO LEGAL**

**Rol:** Actúa como un analista legal senior con la habilidad de sintetizar información compleja de múltiples documentos judiciales en un resumen ejecutivo claro, preciso y estructurado.
**Objetivo:** Tu tarea es generar un **documento de texto en formato Markdown** titulado "Ficha Técnica del Caso: Amparo Directo en Revisión {expediente}". Este documento debe resumir de manera esquemática y cronológica todo el flujo del caso legal a partir de los archivos de texto adjuntos (que son resúmenes en formato JSON de los documentos originales). El reporte debe ser auto-contenido y permitir a un lector entender el caso de principio a fin de manera rápida y eficiente.
**Análisis y Estructura del Contenido:** Analiza la totalidad de los documentos proporcionados para extraer y organizar la información en las siguientes secciones obligatorias y en este orden estricto:
1. **Título Principal:** `### Ficha Técnica del Caso: Amparo Directo en Revisión {expediente}`
2. **Introducción Breve:** Un párrafo que explique el propósito del documento.
3. **Sección 1: Partes Involucradas:**
   * Identifica y lista a los actores clave del proceso bajo los siguientes subtítulos:
      * **Quejoso (Afectado):**
      * **Autoridad Responsable (Acto de Origen):**
      * **Autoridad de Amparo (Recurrida):**
      * **Máximo Tribunal (Resolutor):**
4. **Sección 2: Cronología de Eventos Clave:**
   * Extrae las fechas de expedición (`fecha_expedicion`) y los eventos más relevantes de cada documento para construir una línea de tiempo cronológica en formato de lista. Cada punto debe incluir la fecha y una descripción concisa del evento.
5. **Sección 3: Documentos y Recursos Fundamentales:**
   * Identifica y lista los documentos procesales que fueron cruciales para el desarrollo del caso (ej. Sentencia inicial, Demanda de Amparo, Recurso de Revisión, Sentencia Definitiva).
6. **Sección 4: Resolución Final de la Suprema Corte:**
   * Sintetiza la decisión final contenida en el último documento del expediente. Explica claramente la decisión tomada y sus fundamentos principales.
7. **Sección 5: Siguientes Pasos:**
   * Basándose en la parte resolutiva, describe en una lista numerada los pasos procesales que deben seguirse después de la decisión.
**Requisitos de Formato y Tono:**
* **Formato de Salida:** Un único documento de texto utilizando **Markdown**.
* **Estructura:** Utiliza encabezados (`###`), subtítulos en negrita (`**Subtítulo:**`), y listas con viñetas o numeradas para una máxima claridad y organización.
* **Tono:** Profesional, objetivo y fáctico. La redacción debe ser concisa y directa, evitando jerga legal excesiva.
* **Idioma:** El documento final debe estar completamente en **español**.
* **Fuente de Datos:** La información debe derivarse exclusivamente de los archivos de texto proporcionados. No se debe inventar ni inferir información que no esté presente en los documentos."""


# Mensajes del sistema
MENSAJES = {
    'inicio': "🚀 Sistema de Análisis Jurisprudencial SCJN",
    'directorio_no_existe': "❌ Error: La carpeta {ruta} no existe",
    'directorio_invalido': "❌ Error: {ruta} no es una carpeta",
    'sin_archivos_soportados': "❌ No se encontraron archivos soportados en la carpeta",
    'expediente_nuevo': "📋 Expediente nuevo - {total} documentos encontrados",
    'expediente_resumiendo': "🔄 Resumiendo expediente - {procesados} procesados, {pendientes} pendientes",
    'expediente_completo': "✅ Todos los documentos ya están procesados",
    'procesamiento_exitoso': "✅ Documento procesado exitosamente",
    'procesamiento_error': "❌ Error procesando documento",
    'reporte_generado': "📊 Reporte ejecutivo generado",
    'bitacora_guardada': "📋 Bitácora guardada",
    'proceso_interrumpido': "⚠️ Proceso interrumpido por el usuario"
}