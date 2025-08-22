from typing import List, Dict
from pydantic import BaseModel, Field, ValidationError

# --- Modelo para la sección de ANTECEDENTES Y TRÁMITE ---

class ContenidoNarrativo(BaseModel):
    subtitulo: str = Field(..., description="El subtítulo de la etapa procesal (ej. 'Recurso de Apelación').")
    texto_narrativo: str = Field(..., description="El párrafo redactado que describe la etapa.")

class SeccionAntecedentes(BaseModel):
    seccion: str = Field(..., pattern=r"^ANTECEDENTES Y TRÁMITE$")
    contenido: List[ContenidoNarrativo] = Field(..., description="Lista ordenada de las etapas procesales narradas.")


# --- Modelo para las secciones de FORMALIDADES ---

class ContenidoTitulado(BaseModel):
    titulo: str = Field(..., description="El título formal de la sección (ej. 'I. COMPETENCIA').")
    contenido: str = Field(..., description="El texto redactado para la sección.")

class SeccionFormalidades(BaseModel):
    seccion_competencia: ContenidoTitulado
    seccion_legitimacion: ContenidoTitulado
    seccion_oportunidad: ContenidoTitulado


# --- Modelo para la sección de ESTUDIO DE PROCEDENCIA ---

class ApartadoProcedencia(BaseModel):
    titulo: str = Field(..., description="El título del apartado (ej. 'Demanda de amparo').")
    contenido: str = Field(..., description="El texto completo redactado para ese apartado, incluyendo las citas integradas.")

class SeccionProcedencia(BaseModel):
    seccion: str = Field(..., pattern=r"^IV. ESTUDIO DE PROCEDENCIA DEL RECURSO$")
    apartados: List[ApartadoProcedencia]


# --- Ejemplo de cómo usarías estos modelos en tu código ---

def generar_y_validar_seccion(prompt: str, contexto: dict, modelo_pydantic: BaseModel) -> BaseModel:
    """
    Simula la generación de una sección con un LLM y la valida con un modelo Pydantic.
    """
    print(f"\n--- Generando y validando con el modelo: {modelo_pydantic.__name__} ---")
    
    # 1. Simulación de la llamada al LLM
    # En tu código real, aquí iría la llamada a la API de la IA
    # Supongamos que la IA devuelve un string JSON
    respuesta_llm_json = simular_respuesta_llm(prompt, modelo_pydantic) # Función hipotética
    
    # 2. El paso crucial: Validación con Pydantic
    try:
        modelo_validado = modelo_pydantic.model_validate_json(respuesta_llm_json)
        print(f"¡Éxito! La respuesta del LLM es estructuralmente válida.")
        
        # 3. Guardar en la DB NoSQL o pasar al siguiente paso
        # ... tu lógica para guardar en la base de datos ...
        
        return modelo_validado
    except ValidationError as e:
        print(f"¡ERROR! La respuesta del LLM no cumple con la estructura esperada.")
        print(e)
        # Aquí podrías implementar lógica de reintento, logging de errores, etc.
        return None

def simular_respuesta_llm(prompt, modelo):
    # Esta función solo devuelve un ejemplo de JSON válido para la demostración
    if modelo == SeccionAntecedentes:
        return """
        {
          "seccion": "ANTECEDENTES Y TRÁMITE",
          "contenido": [
            { "subtitulo": "Juicio de Origen", "texto_narrativo": "Texto simulado..." }
          ]
        }
        """
    if modelo == SeccionFormalidades:
        return """
        {
          "seccion_competencia": { "titulo": "I. COMPETENCIA", "contenido": "Texto simulado..." },
          "seccion_legitimacion": { "titulo": "II. LEGITIMACIÓN", "contenido": "Texto simulado..." },
          "seccion_oportunidad": { "titulo": "III. OPPORTUNIDAD", "contenido": "Texto simulado..." }
        }
        """ # Error intencional en OPORTUNIDAD
    return "{}"

# --- Simulación del pipeline ---
# generar_y_validar_seccion("prompt_antecedentes.txt", {}, SeccionAntecedentes)
# generar_y_validar_seccion("prompt_formalidades.txt", {}, SeccionFormalidades)