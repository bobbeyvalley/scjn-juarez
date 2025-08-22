"""
Cliente para interacción con Gemini API
"""

import os
import time
import json
import base64
from typing import Dict, Any, Optional, Tuple
from google import genai
from google.genai import types

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API Key de Gemini no encontrada")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash"
        
        # Prompts predefinidos
        self.mapeo_prompt = self._load_mapeo_prompt()
        self.reporte_prompt = self._load_reporte_prompt()
    
    def _load_mapeo_prompt(self) -> str:
        """Carga el prompt para mapeo de documentos - Versión V2"""
        return """Actúa como un experto analista legal especializado en el sistema judicial mexicano. Tu tarea es extraer información estructurada de documentos judiciales para reconstruir la cronología de un caso ante la Suprema Corte de Justicia de la Nación. Analiza el documento proporcionado y completa los siguientes campos con la máxima precisión.

    IMPORTANTE: El campo 'etapa_procesal_resuelta' DEBE ser uno de los siguientes valores exactos:
    - 'Juicio de Origen'
    - 'Recurso de Apelación' 
    - 'Demanda de Amparo'
    - 'Sentencia de Amparo Directo'
    - 'Recurso de Revisión'
    - 'Acuerdo de Admisión de Revisión'
    - 'Avocamiento'
    - 'Otra'

    LÍMITES ESTRICTOS (CRÍTICO PARA FUNCIONAMIENTO):
    - "titulo": MÁXIMO 50 caracteres
    - "resumen": MÁXIMO 120 caracteres
    - "planteamiento_acto_reclamado": MÁXIMO 280 caracteres
    - "citas": MÁXIMO 500 caracteres cada fragmento textual

    Si un resumen natural excede 120 caracteres, DEBES resumirlo más sin perder el sentido.

    Responde ÚNICAMENTE con un objeto JSON con esta estructura exacta:
    {
    "documento": "Nombre exacto del archivo",
    "identificacion_basica": {
        "tipo_documento": "Tipo de actuación",
        "etapa_procesal_resuelta": "Valor del enum exacto",
        "fecha_resolucion": "AAAA-MM-DD",
        "organo_emisor": "Tribunal que emite",
        "expedientes_principales": ["array de expedientes"],
        "folios": numero_o_null
    },
    "partes": {
        "quejoso_recurrente": "Nombre",
        "autoridad_responsable": "Autoridad",
        "terceros_interesados": ["array o null"]
    },
    "planteamiento_acto_reclamado": "Resumen ≤ 280 chars",
    "puntos_analisis": [
        {
        "titulo": "≤ 10 palabras",
        "resumen": "≤ 120 chars", 
        "pagina": numero,
        "citas": ["fragmentos textuales ≤ 500 chars"]
        }
    ],
    "decision_o_resolutivos": {
        "sentido_del_fallo": "Resultado principal",
        "puntos_resolutivos": ["array de puntos resolutivos"]
    },
    "normas_invocadas": ["array de normas"],
    "metadatos_ubicacion": {
        "paginas_pdf": [inicio, fin]
    }
    }"""

    def _load_reporte_prompt(self) -> str:
        """Carga el prompt para generación de reportes ejecutivos"""
        return """**PROMPT PARA GENERACIÓN DE REPORTE EJECUTIVO DE CASO LEGAL**

**Rol:** Actúa como un analista legal senior con la habilidad de sintetizar información compleja de múltiples documentos judiciales en un resumen ejecutivo claro, preciso y estructurado.
**Objetivo:** Tu tarea es generar un **documento de texto en formato Markdown** titulado "Ficha Técnica del Caso: Amparo Directo en Revisión [EXPEDIENTE]". Este documento debe resumir de manera esquemática y cronológica todo el flujo del caso legal a partir de los archivos de texto adjuntos (que son resúmenes en formato JSON de los documentos originales). El reporte debe ser auto-contenido y permitir a un lector entender el caso de principio a fin de manera rápida y eficiente.
**Análisis y Estructura del Contenido:** Analiza la totalidad de los documentos proporcionados para extraer y organizar la información en las siguientes secciones obligatorias y en este orden estricto:
1. **Título Principal:** `### Ficha Técnica del Caso: Amparo Directo en Revisión [EXPEDIENTE]`
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

    def procesar_documento(self, contenido: str, nombre_archivo: str, 
                          tipo_contenido: str = "text") -> Tuple[Dict[str, Any], int]:
        """
        Procesa un documento individual y retorna el JSON estructurado
        
        Args:
            contenido: Contenido del documento (texto o base64 para binarios)
            nombre_archivo: Nombre del archivo original
            tipo_contenido: 'text', 'pdf', 'image'
        
        Returns:
            Tuple[Dict, int]: (JSON resultado, tokens utilizados)
        """
        start_time = time.time()
        
        # Preparar contenido según tipo
        if tipo_contenido == "text":
            parts = [types.Part.from_text(text=contenido)]
        elif tipo_contenido == "pdf":
            parts = [types.Part.from_bytes(
                mime_type="application/pdf",
                data=base64.b64decode(contenido)
            )]
        elif tipo_contenido == "image":
            # Detectar tipo MIME de imagen
            mime_type = self._detect_image_mime(contenido)
            parts = [types.Part.from_bytes(
                mime_type=mime_type,
                data=base64.b64decode(contenido)
            )]
        else:
            raise ValueError(f"Tipo de contenido no soportado: {tipo_contenido}")

        contents = [
            types.Content(role="user", parts=parts)
        ]

        config = types.GenerateContentConfig(
            temperature=0,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            response_mime_type="application/json",
            system_instruction=[
                types.Part.from_text(text=self.mapeo_prompt)
            ]
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )
            
            # Extraer tokens utilizados (estimación)
            tokens_estimados = len(contenido) // 4  # Aproximación
            
            # Parsear respuesta JSON
            resultado = json.loads(response.text)
            
            return resultado, tokens_estimados
            
        except Exception as e:
            raise Exception(f"Error procesando documento {nombre_archivo}: {str(e)}")

    def generar_reporte_ejecutivo(self, documentos_json: list[Dict[str, Any]], 
                                expediente: str) -> Tuple[str, int]:
        """
        Genera reporte ejecutivo a partir de documentos JSON procesados
        
        Args:
            documentos_json: Lista de documentos ya procesados en JSON
            expediente: Número de expediente
            
        Returns:
            Tuple[str, int]: (Contenido markdown, tokens utilizados)
        """
        # Preparar contenido combinado
        contenido_combinado = "\n\n".join([
            f"=== DOCUMENTO: {doc.get('documento', 'SIN_NOMBRE')} ===\n{json.dumps(doc, indent=2, ensure_ascii=False)}"
            for doc in documentos_json
        ])
        
        prompt_personalizado = self.reporte_prompt.replace("[EXPEDIENTE]", expediente)
        
        contents = [
            types.Content(
                role="user", 
                parts=[types.Part.from_text(text=contenido_combinado)]
            )
        ]

        config = types.GenerateContentConfig(
            temperature=0,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            response_mime_type="text/plain",
            system_instruction=[
                types.Part.from_text(text=prompt_personalizado)
            ]
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )
            
            tokens_estimados = len(contenido_combinado) // 4
            
            return response.text, tokens_estimados
            
        except Exception as e:
            raise Exception(f"Error generando reporte ejecutivo: {str(e)}")

    def _detect_image_mime(self, base64_content: str) -> str:
        """Detecta tipo MIME de imagen basado en contenido"""
        # Implementación básica - se puede mejorar
        if base64_content.startswith("/9j/"):
            return "image/jpeg"
        elif base64_content.startswith("iVBORw0KGgo"):
            return "image/png"
        else:
            return "image/jpeg"  # Default