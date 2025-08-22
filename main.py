#!/usr/bin/env python3
"""
Sistema de Análisis Jurisprudencial SCJN - Versión Consola
Procesa documentos legales y genera análisis estructurados
"""

import os
import sys
import json
import argparse
import hashlib
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import time
from tqdm import tqdm

# Agregar directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

#from core.models import SCJN_Documento, DocumentoMetadata, BitacoraEntry, ExpedienteInfo | Import anterior
from core.models import DocumentoMetadata, BitacoraEntry, ExpedienteInfo
from core.gemini_client import GeminiClient
from processors.pdf_processor import PDFProcessor
from processors.docx_processor import DOCXProcessor
from processors.txt_processor import TXTProcessor
from processors.image_processor import ImageProcessor
from proyecto_sentencia.models_extraccion import SCJNDocumentoMapeado
from proyecto_sentencia import crear_contexto_del_caso_robusto

class ConfiguracionProcesamiento:
    """Parámetros configurables del procesamiento"""
    def __init__(self):
        self.timeout_base_segundos = 120
        self.max_reintentos = 2
        self.pausa_entre_reintentos_segundos = 5
        self.pausa_entre_documentos_segundos = 2.0
        self.region_gcp = "us-central1"

class SCJNAnalyzer:
    def __init__(self, config: ConfiguracionProcesamiento = None):
        self.gemini_client = GeminiClient()
        self.config = config or ConfiguracionProcesamiento()
        self.processors = {
            '.pdf': PDFProcessor(),
            '.docx': DOCXProcessor(),
            '.doc': DOCXProcessor(),
            '.txt': TXTProcessor(),
            '.jpg': ImageProcessor(),
            '.jpeg': ImageProcessor(),
            '.png': ImageProcessor(),
            '.tiff': ImageProcessor(),
            '.tif': ImageProcessor()
        }
        
        # Estado del procesamiento
        self.expediente_actual = None
        self.carpeta_expediente = None
        self.bitacora: List[BitacoraEntry] = []
        self.tokens_totales = 0
        self.tiempo_total = 0
        self.proceso_interrumpido = False
        
        # Configurar handler para Ctrl+C
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Maneja interrupción del usuario (Ctrl+C)"""
        print("\n⚠️ Interrupción detectada. Guardando avances...")
        self.proceso_interrumpido = True
        if self.bitacora and self.expediente_actual:
            self.guardar_bitacora(self.expediente_actual)
        print("💾 Avances guardados. Puedes reanudar ejecutando el comando nuevamente.")
        sys.exit(0)

    def setup_directories_for_expediente(self, carpeta_expediente: Path):
        """Crear directorios de salida dentro de la carpeta del expediente"""
        self.carpeta_expediente = carpeta_expediente
        self.dirs = {
            'jsons': carpeta_expediente / "jsons",
            'reporte': carpeta_expediente / "reporte"
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

    def cargar_bitacora_existente(self, expediente: str) -> Tuple[List[BitacoraEntry], int, float]:
        """Carga bitácora existente si existe"""
        ruta_bitacora = self.dirs['jsons'] / "bitacora_proceso.json"
        
        if not ruta_bitacora.exists():
            return [], 0, 0.0
        
        try:
            with open(ruta_bitacora, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            bitacora_entries = []
            tokens_acumulados = 0
            tiempo_acumulado = 0.0
            
            for entry_dict in data.get('bitacora_detallada', []):
                # Reconstruir BitacoraEntry desde dict
                entry = BitacoraEntry(**entry_dict)
                bitacora_entries.append(entry)
                
                if entry.status == "success" and entry.metadata.tokens_utilizados:
                    tokens_acumulados += entry.metadata.tokens_utilizados
                if entry.metadata.tiempo_procesamiento:
                    tiempo_acumulado += entry.metadata.tiempo_procesamiento
            
            resumen = data.get('resumen_expediente', {})
            return bitacora_entries, tokens_acumulados, tiempo_acumulado
            
        except Exception as e:
            print(f"⚠️ Error cargando bitácora existente: {e}")
            return [], 0, 0.0

    def listar_documentos_soportados(self, carpeta: Path) -> List[Path]:
        """Lista todos los documentos soportados en la carpeta"""
        documentos = []
        documentos_vistos = set()  # Para evitar duplicados
    
        for extension in self.processors.keys():
            for archivo in carpeta.glob(f"*{extension}"):
                if archivo.name not in documentos_vistos:
                    documentos.append(archivo)
                    documentos_vistos.add(archivo.name)

        return sorted(documentos)

    def analizar_estado_expediente(self, carpeta_expediente: Path, expediente: str) -> Tuple[List[Path], str]:
        """Analiza qué documentos faltan por procesar"""
        documentos_disponibles = self.listar_documentos_soportados(carpeta_expediente)
        bitacora_existente, tokens_prev, tiempo_prev = self.cargar_bitacora_existente(expediente)
        
        if not bitacora_existente:
            return documentos_disponibles, f"Expediente nuevo - {len(documentos_disponibles)} documentos encontrados"
        
        # Cargar bitácora y tokens previos
        self.bitacora = bitacora_existente
        self.tokens_totales = tokens_prev
        self.tiempo_total = tiempo_prev
        
        docs_procesados_exitosamente = {
            entry.documento for entry in bitacora_existente 
            if entry.status == "success"
        }
        
        docs_pendientes = [
            doc for doc in documentos_disponibles 
            if doc.name not in docs_procesados_exitosamente
        ]
        
        if not docs_pendientes:
            return [], f"Expediente completo - {len(documentos_disponibles)} documentos ya procesados"
        
        procesados = len(documentos_disponibles) - len(docs_pendientes)
        return docs_pendientes, f"Resumiendo expediente - {procesados} procesados, {len(docs_pendientes)} pendientes"

    def calcular_hash_archivo(self, ruta_archivo: Path) -> str:
        """Calcula hash SHA256 del archivo"""
        sha256_hash = hashlib.sha256()
        with open(ruta_archivo, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def procesar_documento_con_timeout(self, ruta_archivo: Path, expediente: str) -> Optional[Dict[str, Any]]:
        """Procesa un documento con timeout y reintentos"""
        
        for intento in range(self.config.max_reintentos + 1):
            try:
                start_time = time.time()
                
                # Obtener metadata del archivo
                stats = ruta_archivo.stat()
                tamano_mb = stats.st_size / (1024 * 1024)
                
                metadata = DocumentoMetadata(
                    nombre_archivo=ruta_archivo.name,
                    formato=ruta_archivo.suffix.lower(),
                    tamano_bytes=stats.st_size,
                    fecha_procesamiento=datetime.now(),
                    hash_archivo=self.calcular_hash_archivo(ruta_archivo)
                )
                
                # Seleccionar procesador
                extension = ruta_archivo.suffix.lower()
                if extension not in self.processors:
                    raise ValueError(f"Formato no soportado: {extension}")
                
                processor = self.processors[extension]
                
                # Extraer contenido con timeout implícito en Gemini
                contenido, tipo_contenido = processor.extraer_contenido(ruta_archivo)
                
                # Procesar con Gemini (con timeout interno)
                resultado_json, tokens_usados = self.gemini_client.procesar_documento(
                    contenido=contenido,
                    nombre_archivo=ruta_archivo.name,
                    tipo_contenido=tipo_contenido
                )
                
                print(f"\n🔍 DEBUG - JSON recibido de Gemini:")
                print(json.dumps(resultado_json, indent=2, ensure_ascii=False))
                
                # TRANSFORMAR ESTRUCTURA ANIDADA A PLANA
            #     def flatten_gemini_response(json_data):
            #         """Convierte la estructura anidada de Gemini a estructura plana para Pydantic"""
            #         flattened = {}
                    
            #         # Copiar campos de nivel superior
            #         flattened["documento"] = json_data.get("documento", "")
                    
            #         # Extraer de identificacion_basica
            #         if "identificacion_basica" in json_data:
            #             ib = json_data["identificacion_basica"]
            #             flattened["tipo"] = ib.get("tipo_documento", "")
            #             flattened["fecha_expedicion"] = ib.get("fecha_expedicion", "")
            #             flattened["organo_emisor"] = ib.get("organo_emisor", "")
            #             expediente_raw = ib.get("expediente_citados", "")
            #             if isinstance(expediente_raw, list):
            #                 flattened["expediente"] = ", ".join(expediente_raw)  # Convertir lista a string
            #             else:
            #                 flattened["expediente"] = str(expediente_raw)
            #             flattened["folios"] = ib.get("numero_fojas", None)
                    
            #         # Extraer de partes_relevantes
            #         if "partes_relevantes" in json_data:
            #             pr = json_data["partes_relevantes"]
            #             flattened["partes"] = {
            #                 "quejoso": pr.get("quejoso_promovente_recurrente", ""),
            #                 "autoridad_responsable": pr.get("autoridad_responsable", ""),
            #                 "terceros_interesados": pr.get("terceros_interesados", None)
            #             }
                    
            #         # Extraer planteamiento
            #         flattened["planteamiento"] = json_data.get("planteamiento_o_acto_reclamado", "")
                    
            #         # Copiar puntos_analisis (ya está bien)
            #         flattened["puntos_analisis"] = json_data.get("puntos_analisis", [])
                    
            #         # Extraer normas (puede tener nombres diferentes)
            #         flattened["normas_invocadas"] = json_data.get("normas_invocadas", 
            #             json_data.get("normas_o_precedentes_invocados", []))
                    
            #         # Extraer pretensiones (puede tener nombres diferentes)
            #         flattened["pretensiones"] = json_data.get("pretensiones", 
            #             json_data.get("pretensiones_o_resolucion", []))
                    
            #         # Extraer de metadatos_de_ubicacion
            #         if "metadatos_de_ubicacion" in json_data:
            #             mu = json_data["metadatos_de_ubicacion"]
            #             flattened["paginas_pdf"] = mu.get("paginas_pdf", [1, 1])
            #         else:
            #             flattened["paginas_pdf"] = json_data.get("paginas_pdf", [1, 1])
                    
            #         return flattened

            #     # TRANSFORMAR EL JSON
            #     resultado_json = flatten_gemini_response(resultado_json)

                print(f"\n🔍 DEBUG - JSON transformado para Pydantic:")
                print(json.dumps(resultado_json, indent=2, ensure_ascii=False))
                print("-" * 50)


                # Validar estructura
                documento_validado = SCJNDocumentoMapeado(**resultado_json)
                
                # Guardar JSON individual
                end_time = time.time()
                metadata.tokens_utilizados = tokens_usados
                metadata.tiempo_procesamiento = end_time - start_time
                
                nombre_salida = f"{ruta_archivo.stem}_mapeado.json"
                ruta_salida = self.dirs['jsons'] / nombre_salida
                
                with open(ruta_salida, 'w', encoding='utf-8') as f:
                    json.dump(resultado_json, f, indent=2, ensure_ascii=False)
                
                # Registrar éxito en bitácora
                entrada_bitacora = BitacoraEntry(
                    timestamp=datetime.now(),
                    expediente=expediente,
                    documento=ruta_archivo.name,
                    status="success",
                    mensaje=f"Procesado exitosamente en intento {intento + 1}. Tokens: {tokens_usados}",
                    metadata=metadata
                )
                self.bitacora.append(entrada_bitacora)
                
                # Actualizar contadores
                self.tokens_totales += tokens_usados
                self.tiempo_total += metadata.tiempo_procesamiento
                
                return resultado_json
                
            except Exception as e:
                if intento < self.config.max_reintentos:
                    print(f"    🔄 Intento {intento + 1} falló: {str(e)} Reintentando en {self.config.pausa_entre_reintentos_segundos}s")
                    time.sleep(self.config.pausa_entre_reintentos_segundos)
                    continue
                else:
                    # Registrar fallo final
                    entrada_error = BitacoraEntry(
                        timestamp=datetime.now(),
                        expediente=expediente,
                        documento=ruta_archivo.name,
                        status="error",
                        mensaje=f"Error después de {self.config.max_reintentos + 1} intentos",
                        metadata=DocumentoMetadata(
                            nombre_archivo=ruta_archivo.name,
                            formato=ruta_archivo.suffix.lower(),
                            tamano_bytes=stats.st_size if 'stats' in locals() else 0,
                            fecha_procesamiento=datetime.now()
                        ),
                        error_detalle=str(e)
                    )
                    self.bitacora.append(entrada_error)
                    return None

    def procesar_expediente_completo(self, carpeta_expediente: Path, expediente: str) -> bool:
        """
        Procesa un expediente completo con resume automático
        
        Returns:
            bool: True si el expediente está completo para generar reporte
        """
        self.expediente_actual = expediente
        self.setup_directories_for_expediente(carpeta_expediente)
        
        print(f"\n🚀 Analizando expediente: {expediente}")
        print(f"📁 Ruta: {carpeta_expediente}")
        print("="*80)
        
        # Analizar estado actual
        docs_pendientes, mensaje_estado = self.analizar_estado_expediente(carpeta_expediente, expediente)
        print(f"📋 {mensaje_estado}")
        
        if not docs_pendientes:
            print("✅ Todos los documentos ya están procesados")
            return self._verificar_expediente_completo(carpeta_expediente)
        
        # Procesar documentos pendientes
        print(f"\n🔄 Procesando {len(docs_pendientes)} documentos pendientes...")
        
        with tqdm(total=len(docs_pendientes), desc="Progreso", 
                 bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}") as pbar:
            
            exitosos_en_sesion = 0
            fallos_en_sesion = 0
            
            for i, archivo in enumerate(docs_pendientes):
                if self.proceso_interrumpido:
                    break
                    
                pbar.set_description(f"Procesando {archivo.name[:30]}...")
                
                resultado = self.procesar_documento_con_timeout(archivo, expediente)
                
                if resultado is not None:
                    exitosos_en_sesion += 1
                    pbar.set_postfix({
                        'exitosos': exitosos_en_sesion,
                        'fallos': fallos_en_sesion,
                        'tokens': f"{self.tokens_totales:,}"
                    })
                else:
                    fallos_en_sesion += 1
                    pbar.set_postfix({
                        'exitosos': exitosos_en_sesion,
                        'fallos': fallos_en_sesion,
                        'tokens': f"{self.tokens_totales:,}"
                    })
                
                pbar.update(1)
                
                # Pausa entre documentos
                if i < len(docs_pendientes) - 1 and not self.proceso_interrumpido:
                    time.sleep(self.config.pausa_entre_documentos_segundos)
        
        # Guardar bitácora actualizada
        self.guardar_bitacora(expediente)
        
        if self.proceso_interrumpido:
            return False
        
        # Verificar si el expediente está completo
        return self._verificar_expediente_completo(carpeta_expediente)

    def _verificar_expediente_completo(self, carpeta_expediente: Path) -> bool:
        """Verifica si todos los documentos del expediente fueron procesados exitosamente"""
        documentos_totales = self.listar_documentos_soportados(carpeta_expediente)
        docs_exitosos = {entry.documento for entry in self.bitacora if entry.status == "success"}
        
        documentos_totales_nombres = {doc.name for doc in documentos_totales}
        
        if documentos_totales_nombres.issubset(docs_exitosos):
            return True
        else:
            faltantes = documentos_totales_nombres - docs_exitosos
            print(f"\n⏳ Expediente incompleto. Documentos faltantes: {len(faltantes)}")
            for doc in sorted(faltantes):
                print(f"   📄 {doc}")
            print("💡 Ejecuta el comando nuevamente para procesar los documentos faltantes")
            return False

    def generar_reporte_ejecutivo(self, expediente: str):
        """Genera reporte ejecutivo del expediente completo"""
        print(f"\n📊 Generando reporte ejecutivo para expediente {expediente}...")
        
        try:
            # Cargar todos los JSONs procesados
            documentos_json = []
            for json_file in self.dirs['jsons'].glob("*_mapeado.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                    documentos_json.append(doc_data)
            
            if not documentos_json:
                raise ValueError("No se encontraron documentos procesados para generar el reporte")
            
            start_time = time.time()
            contenido_markdown, tokens_usados = self.gemini_client.generar_reporte_ejecutivo(
                documentos_json, expediente
            )
            end_time = time.time()
            
            # Guardar reporte
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_reporte = f"reporte_ejecutivo_{expediente}_{timestamp}.md"
            ruta_reporte = self.dirs['reporte'] / nombre_reporte
            
            with open(ruta_reporte, 'w', encoding='utf-8') as f:
                f.write(contenido_markdown)
            
            # Actualizar contadores
            self.tokens_totales += tokens_usados
            self.tiempo_total += (end_time - start_time)
            
            print(f"  ✅ Reporte generado: {ruta_reporte.name}")
            print(f"  📊 Tokens utilizados: {tokens_usados:,}")
            print(f"  📄 Documentos analizados: {len(documentos_json)}")
            
        except Exception as e:
            print(f"  ❌ Error generando reporte: {e}")

    def guardar_bitacora(self, expediente: str):
        """Guarda la bitácora en la carpeta jsons del expediente"""
        ruta_bitacora = self.dirs['jsons'] / "bitacora_proceso.json"
        
        # Preparar datos de la bitácora
        bitacora_dict = []
        for entry in self.bitacora:
            entry_dict = entry.model_dump()
            # Convertir datetime a string para serialización
            entry_dict['timestamp'] = entry.timestamp.isoformat()
            entry_dict['metadata']['fecha_procesamiento'] = entry.metadata.fecha_procesamiento.isoformat()
            bitacora_dict.append(entry_dict)
        
        # Contar estadísticas
        docs_exitosos = [entry for entry in self.bitacora if entry.status == "success"]
        total_documentos_disponibles = len(self.listar_documentos_soportados(self.carpeta_expediente))
        
        info_expediente = {
            "numero_expediente": expediente,
            "fecha_inicio": datetime.now().isoformat(),
            "documentos_procesados": [entry.documento for entry in docs_exitosos],
            "total_documentos_disponibles": total_documentos_disponibles,
            "total_documentos_procesados": len(docs_exitosos),
            "total_documentos_fallidos": len(self.bitacora) - len(docs_exitosos),
            "tokens_totales": self.tokens_totales,
            "tiempo_total_procesamiento": self.tiempo_total,
            "expediente_completo": len(docs_exitosos) == total_documentos_disponibles
        }
        
        bitacora_completa = {
            "resumen_expediente": info_expediente,
            "bitacora_detallada": bitacora_dict
        }
        
        with open(ruta_bitacora, 'w', encoding='utf-8') as f:
            json.dump(bitacora_completa, f, indent=2, ensure_ascii=False)

    def mostrar_resumen_final(self, expediente_completo: bool = False):
        """Muestra resumen final del procesamiento"""
        exitosos = len([e for e in self.bitacora if e.status == "success"])
        errores = len([e for e in self.bitacora if e.status == "error"])
        
        print("\n" + "="*80)
        if expediente_completo:
            print("🎉 EXPEDIENTE COMPLETADO")
        else:
            print("📋 PROCESAMIENTO FINALIZADO")
        print("="*80)
        print(f"📄 Documentos procesados exitosamente: {exitosos}")
        print(f"❌ Documentos con errores: {errores}")
        print(f"🔤 Total de tokens utilizados: {self.tokens_totales:,}")
        print(f"⏱️ Tiempo total de procesamiento: {self.tiempo_total:.2f} segundos")
        # print(f"💰 Costo estimado (aprox): ${self.tokens_totales * 0.000001:.4f} USD")
        
        if expediente_completo:
            print("📊 Reporte ejecutivo generado")
        
        print("="*80)

def ejecutar_generacion_proyecto(carpeta_expediente: Path, expediente: str):
    """Ejecuta la generación del proyecto de sentencia"""
    try:
        # Buscar JSONs procesados en la carpeta jsons/
        carpeta_jsons = carpeta_expediente / "jsons"
        if not carpeta_jsons.exists():
            print("❌ Error: No se encontró carpeta 'jsons'. Ejecuta primero la extracción.")
            return
        
        # Buscar archivos JSON mapeados
        archivos_json = list(carpeta_jsons.glob("*_mapeado.json"))
        if not archivos_json:
            print("❌ Error: No se encontraron archivos JSON mapeados.")
            return
        
        print(f"📁 Encontrados {len(archivos_json)} documentos procesados")
        
        # Crear contexto del caso
        print("🔄 Consolidando contexto cronológico...")
        contexto = crear_contexto_del_caso_robusto(
            lista_archivos_json=[str(f) for f in archivos_json],
            id_caso=expediente,
            output_dir=str(carpeta_expediente)
        )
        
        print(f"✅ Contexto generado: CONTEXTO_{expediente}.json")
        print("🎉 ¡Proyecto de sentencia listo para generación de secciones!")
        
    except Exception as e:
        print(f"❌ Error en generación de proyecto: {e}")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Procesador de Expedientes SCJN')
    parser.add_argument('--expediente', type=str, required=True, 
                       help='Ruta a la carpeta del expediente')
    parser.add_argument('--modo', choices=['extraccion', 'proyecto', 'completo'], 
                       default='completo', help='Modo de procesamiento')
    parser.add_argument('--timeout', type=int, default=120,
                       help='Timeout por documento en segundos (default: 120)')
    parser.add_argument('--reintentos', type=int, default=2,
                       help='Número máximo de reintentos (default: 2)')
    
    args = parser.parse_args()
    
    # Validar ruta del expediente
    carpeta_expediente = Path(args.expediente)
    if not carpeta_expediente.exists():
        print(f"❌ Error: La carpeta {carpeta_expediente} no existe")
        sys.exit(1)
    
    if not carpeta_expediente.is_dir():
        print(f"❌ Error: {carpeta_expediente} no es una carpeta")
        sys.exit(1)
    
    # Extraer nombre del expediente de la carpeta
    expediente = carpeta_expediente.name
    
    # Configurar procesamiento
    config = ConfiguracionProcesamiento()
    config.timeout_base_segundos = args.timeout
    config.max_reintentos = args.reintentos
    
    # Crear analizador
    analyzer = SCJNAnalyzer(config)
    
    try:
        # 🆕 LÓGICA EXTENDIDA POR MODO
        if args.modo in ['extraccion', 'completo']:
            print("🚀 Ejecutando extracción de documentos...")
            expediente_completo = analyzer.procesar_expediente_completo(carpeta_expediente, expediente)
            
            if expediente_completo:
                analyzer.generar_reporte_ejecutivo(expediente)
            
            analyzer.mostrar_resumen_final(expediente_completo)
        
        if args.modo in ['proyecto', 'completo']:
            print("\n📋 Ejecutando generación de proyecto de sentencia...")
            ejecutar_generacion_proyecto(carpeta_expediente, expediente)
            
    except KeyboardInterrupt:
        print("\n🛑 Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()