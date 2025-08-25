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

    # AGREGAR ESTOS MÉTODOS AL FINAL DE LA CLASE GeminiClient en core/gemini_client.py

    def generar_seccion(self, prompt_type: str, contexto: dict, 
                    response_format: str = "application/json") -> Tuple[Dict[str, Any], int]:
        """
        Genera una sección específica del proyecto de sentencia
        
        Args:
            prompt_type: Tipo de sección ('antecedentes', 'formalidades', 'procedencia')
            contexto: Diccionario con el contexto del caso (CONTEXTO_{expediente}.json)
            response_format: Formato de respuesta ('application/json' o 'text/plain')
        
        Returns:
            Tuple[Dict|str, int]: (Resultado, tokens utilizados)
        """
        start_time = time.time()
        
        # Cargar prompt específico según el tipo
        prompt_template = self._load_seccion_prompt(prompt_type)
        
        # Insertar contexto en el prompt
        prompt_completo = self._insertar_contexto_en_prompt(prompt_template, contexto)
        
        # Preparar contenido para Gemini
        contents = [
            types.Content(
                role="user", 
                parts=[types.Part.from_text(text=json.dumps(contexto, indent=2, ensure_ascii=False))]
            )
        ]

        config = types.GenerateContentConfig(
            temperature=0,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            response_mime_type=response_format,
            system_instruction=[
                types.Part.from_text(text=prompt_completo)
            ]
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )
            
            # Calcular tokens estimados
            tokens_estimados = len(json.dumps(contexto)) // 4
            
            # # # 🆕 DEBUG: GUARDAR RESPUESTA RAW ANTES DE PARSEAR
            # if prompt_type == "procedencia":  # Solo para la sección problemática
            #     debug_file = f"debug_response_{prompt_type}_{int(time.time())}.txt"
            #     with open(debug_file, 'w', encoding='utf-8') as f:
            #         f.write("=== RESPUESTA CRUDA DE GEMINI ===\n")
            #         f.write(response.text)
            #         f.write("\n\n=== FIN DE RESPUESTA ===")
            #     print(f"🐛 DEBUG: Respuesta guardada en {debug_file}")
                
            #     # También imprimir los primeros y últimos caracteres
            #     print(f"🐛 DEBUG: Primeros 500 chars: {response.text[:500]}")
            #     print(f"🐛 DEBUG: Últimos 500 chars: {response.text[-500:]}")
            #     print(f"🐛 DEBUG: Longitud total: {len(response.text)} caracteres")

            # Parsear respuesta según formato
            if response_format == "application/json":
                resultado = json.loads(response.text)
            else:
                resultado = response.text
            
            return resultado, tokens_estimados
            
        except Exception as e:
            raise Exception(f"Error generando sección {prompt_type}: {str(e)}")

    def _load_seccion_prompt(self, prompt_type: str) -> str:
        """Carga el prompt específico para cada tipo de sección"""
        
        prompts = {
            'antecedentes': """# ROL Y OBJETIVO
    Actúa como Secretario de Estudio y Cuenta de la Suprema Corte de Justicia de la Nación. Tu tarea es redactar la sección de 'ANTECEDENTES Y TRÁMITE' de un proyecto de sentencia.

    # CONTEXTO
    A continuación, te proporciono un JSON que contiene la cronología de hitos procesales de un caso, desde su origen hasta su llegada a esta Suprema Corte. Cada hito contiene información clave como las partes, la fecha, el órgano emisor y el sentido del fallo.

    # TAREA
    1. Lee cronológicamente cada uno de los "hitos_procesales".
    2. Para cada hito, redacta un párrafo claro, conciso y en lenguaje jurídico formal que describa lo sucedido en esa etapa. Utiliza la información proporcionada en cada objeto JSON del hito para tu redacción.
    3. **REFERENCIAS OBLIGATORIAS**: En cada párrafo, DEBES incluir referencias explícitas al documento original usando el siguiente formato:
    - "Conforme se desprende de [tipo de documento] ([nombre_archivo], página X)..."
    - "Según consta en [tipo de documento] ([nombre_archivo], páginas X-Y)..."
    - "Como se advierte del [tipo de documento] ([nombre_archivo], folio X)..."
    
    Donde:
    - [tipo de documento] = etapa_procesal_resuelta en español (ej. "demanda de amparo", "sentencia recurrida", "recurso de revisión")
    - [nombre_archivo] = campo "documento" exacto
    - página/páginas = extraído de "paginas_pdf" o "puntos_analisis[].pagina"

    4. Estructura tu respuesta en un formato JSON que contenga una lista de objetos, donde cada objeto represente un subtítulo y el texto narrativo correspondiente a esa etapa del proceso.

    # FORMATO DE SALIDA
    Tu respuesta debe ser únicamente un objeto JSON válido con la siguiente estructura:
    {
    "seccion": "ANTECEDENTES Y TRÁMITE",
    "contenido": [
        { "subtitulo": "Juicio de Origen", "texto_narrativo": "..." },
        { "subtitulo": "Sentencia Definitiva", "texto_narrativo": "..." },
        { "subtitulo": "Recurso de Apelación", "texto_narrativo": "..." },
        { "subtitulo": "Primer Juicio de Amparo Directo", "texto_narrativo": "..." },
        { "subtitulo": "Segundo Juicio de Amparo Directo", "texto_narrativo": "..." },
        { "subtitulo": "Recurso de Revisión", "texto_narrativo": "..." },
        { "subtitulo": "Trámite ante esta Suprema Corte", "texto_narrativo": "..." }
    ]
    }

    **EJEMPLO DE PÁRRAFO CON REFERENCIAS:**
    "Mediante escrito presentado el veinticuatro de marzo de dos mil veintitrés, conforme se desprende de la demanda de amparo directo (AD. 71/2023, páginas 1-33), VINICIO ANDRES PEÑA TAMAYO, por propio derecho, promovió juicio de amparo directo contra la sentencia definitiva..."
    """,

            'formalidades': """# ROL Y OBJETIVO
    Actúa como un redactor jurídico de la Suprema Corte. Tu tarea es generar los textos para las secciones de 'COMPETENCIA', 'LEGITIMACIÓN' y 'OPORTUNIDAD' de un proyecto de sentencia.

    # TAREA
    1. **Para COMPETENCIA:** Redacta el párrafo estándar, citando los artículos de la Constitución, Ley de Amparo y Ley Orgánica del Poder Judicial de la Federación que se mencionan en los documentos.
    2. **Para LEGITIMACIÓN:** Redacta un párrafo que establezca que la parte recurrente está legitimada para interponer el recurso, indicando su carácter en el juicio de amparo.
    3. **Para OPORTUNIDAD:** Redacta el párrafo que narra el cómputo del plazo. Indica la fecha de notificación de la sentencia recurrida, cuándo surtió efectos, el periodo del plazo de diez días, los días inhábiles que se descontaron y la fecha de presentación del recurso.

    # REFERENCIAS OBLIGATORIAS
    **DEBES incluir referencias a los documentos originales en cada sección usando este formato:**
    - "Según se advierte del acuerdo de admisión ([nombre_archivo], página X)..."
    - "Conforme consta en el recurso de revisión ([nombre_archivo], páginas X-Y)..."
    - "Como se desprende de la notificación ([nombre_archivo])..."

    **EXTRAE las fechas, plazos y datos específicos directamente de los documentos del contexto proporcionado.**

    # FORMATO DE SALIDA
    Tu respuesta debe ser únicamente un objeto JSON válido con la siguiente estructura:
    {
    "seccion_competencia": { "titulo": "I. COMPETENCIA", "contenido": "..." },
    "seccion_legitimacion": { "titulo": "II. LEGITIMACIÓN", "contenido": "..." },
    "seccion_oportunidad": { "titulo": "III. OPORTUNIDAD", "contenido": "..." }
    }

    **EJEMPLO CON REFERENCIAS:**
    "El recurso de revisión fue interpuesto de forma oportuna. Según se advierte del oficio de notificación (Oficio de Notificación de Sentencia de Amparo Directo, página 1), la sentencia recurrida se notificó por oficio el nueve de agosto de dos mil veintitrés..."
    """,

            'procedencia': """# TAREA
    1. Redacta un párrafo introductorio para la sección, titulado "Cuestiones necesarias para analizar el asunto".
    2. **Redacta el apartado "Demanda de amparo":**
    * Crea un párrafo introductorio.
    * Para cada "punto_analisis" relevante de la demanda, redacta un párrafo que describa el argumento del quejoso.
    * **CRUCIAL:** Dentro de tu redacción, debes integrar de forma natural y fluida la cita textual exacta ("citas.texto") que corresponde a ese argumento. No la pongas solo al final, insértala como parte de la narrativa.
    3. **Redacta el apartado "Sentencia del Tribunal Colegiado":**
    * Resume la decisión y razonamientos del Tribunal Colegiado, usando sus "puntos_analisis" e integrando sus citas textuales de la misma manera.
    4. **Redacta el apartado "Agravios de Revisión":**
    * Describe los argumentos del recurrente en su recurso de revisión, usando sus "puntos_analisis" e integrando sus citas.
    5. **Redacta el apartado "Procedencia en el Caso Concreto":**
    * Con base en todo lo anterior, redacta el análisis final que concluye si el recurso es procedente porque subsiste un tema de constitucionalidad de interés excepcional.

    # REFERENCIAS OBLIGATORIAS EN CADA APARTADO
    **DEBES incluir referencias específicas a los documentos originales:**

    - **Para Demanda de amparo:** "Conforme se desprende de la demanda de amparo ([nombre_archivo], páginas X-Y)..."
    - **Para Sentencia del Tribunal:** "Según consta en la sentencia recurrida ([nombre_archivo], página X)..."
    - **Para Agravios de Revisión:** "Como se advierte del recurso de revisión ([nombre_archivo], páginas X-Y)..."
    - **Para Procedencia:** "Según se estableció en el acuerdo de admisión ([nombre_archivo], página X)..."

    **EXTRAE la información específica de páginas de los campos:**
    - `puntos_analisis[].pagina` para referencias específicas
    - `paginas_pdf` para rangos de páginas del documento
    - `documento` para el nombre exacto del archivo

    # FORMATO DE SALIDA
    Tu respuesta debe ser únicamente un objeto JSON válido con la siguiente estructura:
    {
    "seccion": "IV. ESTUDIO DE PROCEDENCIA DEL RECURSO",
    "apartados": [
        { "titulo": "Cuestiones necesarias para analizar el asunto", "contenido": "..." },
        { "titulo": "Demanda de amparo", "contenido": "..." },
        { "titulo": "Sentencia del Tribunal Colegiado", "contenido": "..." },
        { "titulo": "Agravios de Revisión", "contenido": "..." },
        { "titulo": "Procedencia en el Caso Concreto", "contenido": "..." }
    ]
    }

    **EJEMPLO CON REFERENCIAS Y CITAS INTEGRADAS:**
    "El quejoso, Vinicio Andrés Peña Tamayo, conforme se desprende de la demanda de amparo directo (AD. 71/2023, página 5), alegó violación a la garantía de legalidad argumentando que 'nadie puede ser privado de la libertad si no se sigue un juicio en que se observen las formalidades esenciales del procedimiento', señalando específicamente que..."
    """
        }
        
        if prompt_type not in prompts:
            raise ValueError(f"Tipo de prompt no reconocido: {prompt_type}. Tipos válidos: {list(prompts.keys())}")
        
        return prompts[prompt_type]

    def _insertar_contexto_en_prompt(self, prompt_template: str, contexto: dict) -> str:
        """Inserta información del contexto en el prompt si es necesario"""
        # Por ahora, el contexto se pasa como contenido separado
        # Pero aquí podrías hacer sustituciones específicas si el prompt lo requiere
        
        # Ejemplo de sustitución dinámica:
        if "expediente_principal" in contexto.get("metadata_caso", {}):
            expediente = contexto["metadata_caso"]["expediente_principal"]
            prompt_template = prompt_template.replace("[EXPEDIENTE]", expediente)
        
        return prompt_template