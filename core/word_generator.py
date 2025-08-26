# core/word_generator.py
"""
Generador de documentos Word profesionales para proyectos de sentencia SCJN
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.shared import OxmlElement, qn

class SCJNWordGenerator:
    """Generador de documentos Word con formato profesional para la SCJN"""
    
    def __init__(self):
        self.doc = None
        self.estilos_configurados = False

    #a ver si esto no rompe todo
    def crear_documento_desde_markdown(self, contenido_markdown: str, expediente: str,
                                 archivo_salida: Path, nombre_ministro: str,
                                 nombre_secretario: str, contexto_caso: dict,
                                 nombre_secretario_aux: str = None,
                                 colaboradores: list = None) -> Path:
        """
        Convierte contenido Markdown a documento Word profesional
        
        Args:
            contenido_markdown: Contenido en formato Markdown
            expediente: Número de expediente para el header
            archivo_salida: Ruta donde guardar el documento Word
            
        Returns:
            Path: Ruta del archivo Word generado
        """
        print("🔍 DEBUG - Iniciando crear_documento_desde_markdown")
            
        self.doc = Document()
        print("🔍 DEBUG - Documento Word creado")
        
        self._configurar_estilos_profesionales()
        print("🔍 DEBUG - Estilos configurados")
        
        self._configurar_pagina()
        print("🔍 DEBUG - Página configurada")
    
        # Agregar header institucional
        self._agregar_header_scjn(
            expediente=expediente,
            nombre_ministro=nombre_ministro,
            nombre_secretario=nombre_secretario,
            contexto_caso=contexto_caso,
            nombre_secretario_aux=nombre_secretario_aux,
            colaboradores=colaboradores
        )

        print("🔍 DEBUG - Header completado")
        
        # Procesar contenido Markdown
        print("🔍 DEBUG - Iniciando procesamiento de Markdown...")
        self._procesar_markdown(contenido_markdown)
        print("🔍 DEBUG - Markdown procesado") 

        # Agregar footer
        print("🔍 DEBUG - Agregando footer...")
        self._agregar_footer()
        print("🔍 DEBUG - Footer agregado")     
    
        # Guardar documento
        print(f"🔍 DEBUG - Guardando documento en: {archivo_salida}")
        self.doc.save(archivo_salida)
        print(f"🔍 DEBUG - Archivo guardado exitosamente: {archivo_salida.exists()}")
        return archivo_salida
  
      

    def _configurar_estilos_profesionales(self):
        """Configura estilos profesionales para documentos SCJN"""
        if self.estilos_configurados:
            return
            
        styles = self.doc.styles
        
        # Estilo para título principal
        try:
            titulo_principal = styles.add_style('TituloPrincipal', WD_STYLE_TYPE.PARAGRAPH)
        except:
            titulo_principal = styles['TituloPrincipal']
        
        titulo_principal.font.name = 'Times New Roman'
        titulo_principal.font.size = Pt(16)
        titulo_principal.font.bold = True
        titulo_principal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        titulo_principal.paragraph_format.space_after = Pt(12)
        
        # Estilo para subtítulos nivel 2
        try:
            subtitulo_h2 = styles.add_style('SubtituloH2', WD_STYLE_TYPE.PARAGRAPH)
        except:
            subtitulo_h2 = styles['SubtituloH2']
            
        subtitulo_h2.font.name = 'Times New Roman'
        subtitulo_h2.font.size = Pt(14)
        subtitulo_h2.font.bold = True
        subtitulo_h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitulo_h2.paragraph_format.space_before = Pt(12)
        subtitulo_h2.paragraph_format.space_after = Pt(6)
        
        # Estilo para subtítulos nivel 3
        try:
            subtitulo_h3 = styles.add_style('SubtituloH3', WD_STYLE_TYPE.PARAGRAPH)
        except:
            subtitulo_h3 = styles['SubtituloH3']
            
        subtitulo_h3.font.name = 'Times New Roman'
        subtitulo_h3.font.size = Pt(12)
        subtitulo_h3.font.bold = True
        subtitulo_h3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        subtitulo_h3.paragraph_format.space_before = Pt(6)
        subtitulo_h3.paragraph_format.space_after = Pt(3)
        
        # Estilo para texto normal
        try:
            texto_normal = styles.add_style('TextoNormal', WD_STYLE_TYPE.PARAGRAPH)
        except:
            texto_normal = styles['TextoNormal']
            
        texto_normal.font.name = 'Times New Roman'
        texto_normal.font.size = Pt(11)
        texto_normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        texto_normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        texto_normal.paragraph_format.space_after = Pt(6)
        texto_normal.paragraph_format.first_line_indent = Inches(0.5)
        
        # Estilo para citas textuales (indentadas)
        try:
            cita_textual = styles.add_style('CitaTextual', WD_STYLE_TYPE.PARAGRAPH)
        except:
            cita_textual = styles['CitaTextual']
            
        cita_textual.font.name = 'Times New Roman'
        cita_textual.font.size = Pt(10)
        cita_textual.font.italic = True
        cita_textual.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        cita_textual.paragraph_format.left_indent = Inches(0.5)
        cita_textual.paragraph_format.right_indent = Inches(0.5)
        cita_textual.paragraph_format.space_before = Pt(3)
        cita_textual.paragraph_format.space_after = Pt(3)
        
        self.estilos_configurados = True

    def _configurar_pagina(self):
        """Configura márgenes y orientación de página"""
        sections = self.doc.sections
        for section in sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.5)
            section.right_margin = Inches(1.0)

    def _agregar_header_scjn(self, expediente: str, nombre_ministro: str, 
                        nombre_secretario: str, contexto_caso: dict,
                        nombre_secretario_aux: str = None, 
                        colaboradores: list = None):
        """Agrega header institucional estilo SCJN con placeholders"""
        
        # Header con datos del caso
        header = self.doc.add_paragraph()
        header.style = 'TituloPrincipal'
        header.paragraph_format.left_indent = Inches(2.0)
        expediente_principal = contexto_caso.get('metadata_caso', {}).get('expediente_principal', f'ASUNTO {expediente}')
        header.add_run(f'{expediente_principal}\n\n')
        header.add_run('[INSERTAR DATOS DEL QUEJOSO]\n\n')
        header.add_run('[INSERTAR DATOS DEL RECURRENTE]')
        
        # Personal jurisdiccional
        personal = self.doc.add_paragraph()
        personal.style = 'TextoNormal'
        personal.add_run(f'PONENTE: MINISTRO {nombre_ministro.upper()}\n\n')
        personal.add_run(f'SECRETARIO: {nombre_secretario.upper()}\n\n')
        
        if nombre_secretario_aux:
            personal.add_run(f'SECRETARIO AUXILIAR: {nombre_secretario_aux.upper()}\n\n')
        
        if colaboradores:
            for colab in colaboradores:
                personal.add_run(f'COLABORÓ: {colab.upper()}\n\n')
        
        # Placeholder para índice temático
        indice = self.doc.add_paragraph()
        indice.style = 'SubtituloH2'
        indice.add_run('ÍNDICE TEMÁTICO\n')
        indice_placeholder = self.doc.add_paragraph()
        indice_placeholder.style = 'TextoNormal'
        indice_placeholder.add_run('[INSERTAR TABLA DE ÍNDICE TEMÁTICO AL FINALIZAR]')

    def _procesar_markdown(self, contenido: str):
        """Procesa el contenido Markdown línea por línea - Versión Segura"""
        print(f"🔍 DEBUG - Procesando {len(contenido)} caracteres de Markdown")
        lineas = contenido.split('\n')
        print(f"🔍 DEBUG - Dividido en {len(lineas)} líneas")
        
        i = 0
        max_iteraciones = len(lineas) * 2  # Límite de seguridad
        iteraciones = 0
        
        while i < len(lineas) and iteraciones < max_iteraciones:
            iteraciones += 1
            
            if iteraciones % 100 == 0:  # Debug cada 100 iteraciones
                print(f"🔍 DEBUG - Iteración {iteraciones}, línea {i}/{len(lineas)}")
            
            linea = lineas[i].strip()
            
            if not linea:
                # Línea vacía - agregar espacio
                self.doc.add_paragraph()
                i += 1
                continue
            
            # Headers
            if linea.startswith('### '):
                # H3 - Subsecciones
                titulo = linea[4:].strip()
                p = self.doc.add_paragraph()
                p.style = 'SubtituloH3'
                p.add_run(titulo)
                i += 1
                continue
            elif linea.startswith('## '):
                # H2 - Secciones principales
                titulo = linea[3:].strip()
                p = self.doc.add_paragraph()
                p.style = 'SubtituloH2'
                p.add_run(titulo)
                i += 1
                continue
            elif linea.startswith('# '):
                # H1 - Título principal (saltar)
                i += 1
                continue
            
            # Líneas de separación
            elif linea.startswith('---') or linea.startswith('==='):
                self.doc.add_paragraph()
                i += 1
                continue
            
            # Texto con formato especial
            elif linea.startswith('**') and linea.endswith('**'):
                # Texto en negrita
                p = self.doc.add_paragraph()
                p.style = 'TextoNormal'
                run = p.add_run(linea[2:-2])
                run.bold = True
                i += 1
                continue
            
            # Advertencias o notas especiales
            elif linea.startswith('*⚠️') or linea.startswith('*Nota:'):
                p = self.doc.add_paragraph()
                p.style = 'CitaTextual'
                texto = linea[1:] if linea.startswith('*') else linea
                p.add_run(texto)
                i += 1
                continue
            
            else:
                # Texto normal - VERSIÓN SEGURA
                p = self.doc.add_paragraph()
                p.style = 'TextoNormal'
                self._agregar_texto_con_formato(p, linea)
                i += 1
                continue
        
        if iteraciones >= max_iteraciones:
            print(f"⚠️ ADVERTENCIA: Procesamiento limitado por seguridad en {max_iteraciones} iteraciones")
        
        print(f"🔍 DEBUG - Markdown procesado en {iteraciones} iteraciones")

    def _agregar_texto_con_formato(self, paragraph, texto: str):
        """Agrega texto con formato inline (negritas, cursivas) preservado"""
        # Expresión regular para encontrar texto en negritas **texto**
        patron_negrita = r'\*\*(.*?)\*\*'
        
        # Dividir texto por partes con y sin formato
        partes = re.split(patron_negrita, texto)
        
        for i, parte in enumerate(partes):
            if not parte:
                continue
                
            if i % 2 == 0:
                # Texto normal
                paragraph.add_run(parte)
            else:
                # Texto en negrita
                run = paragraph.add_run(parte)
                run.bold = True

    def _agregar_footer(self):
        """Agrega footer con información de generación"""
        self.doc.add_page_break()
        
        # Footer informativo
        footer_p = self.doc.add_paragraph()
        footer_p.style = 'CitaTextual'
        footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        fecha_generacion = datetime.now().strftime('%d de %B de %Y')
        footer_text = f"""
Este documento fue generado automáticamente por el Sistema de Análisis Jurisprudencial SCJN.
Fecha de generación: {fecha_generacion}
Revisión y validación jurídica requerida antes de su uso oficial.
        """.strip()
        
        footer_p.add_run(footer_text)

def convertir_markdown_a_word(archivo_markdown: Path, expediente: str, 
                             carpeta_salida: Path, contexto_caso: dict,
                             nombre_ministro: str, nombre_secretario: str, 
                             nombre_secretario_aux: str = None,
                             colaboradores: list = None) -> Path:
    """
    Función utilitaria para convertir un archivo Markdown a Word
    
    Args:
        archivo_markdown: Ruta del archivo .md a convertir
        expediente: Número de expediente
        carpeta_salida: Carpeta donde guardar el archivo Word
        
    Returns:
        Path: Ruta del archivo Word generado
    """
    if not archivo_markdown.exists():
        raise FileNotFoundError(f"Archivo Markdown no encontrado: {archivo_markdown}")
    
    # Leer contenido Markdown
    with open(archivo_markdown, 'r', encoding='utf-8') as f:
        contenido_markdown = f.read()
    
    # Crear nombre de archivo Word
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_word = f"proyecto_sentencia_{expediente}_{timestamp}.docx"
    archivo_word = carpeta_salida / nombre_word
    
    print(f"🔍 DEBUG Word - Datos recibidos:")
    print(f"  - carpeta_salida: {carpeta_salida}")
    print(f"  - nombre_word: {nombre_word}")
    print(f"  - archivo_word completo: {archivo_word}")
    print(f"  - carpeta_salida existe? {carpeta_salida.exists()}")

    # Generar documento Word
    generator = SCJNWordGenerator()
    print(f"🔍 DEBUG - Guardando Word en: {archivo_word}")
    generator.crear_documento_desde_markdown(
        contenido_markdown=contenido_markdown,
        expediente=expediente,
        archivo_salida=archivo_word,
        contexto_caso=contexto_caso,
        nombre_ministro=nombre_ministro,
        nombre_secretario=nombre_secretario,
        nombre_secretario_aux=nombre_secretario_aux,
        colaboradores=colaboradores
    )
    
    print(f"🔍 DEBUG - Word guardado exitosamente: {archivo_word.exists()}")
    return archivo_word