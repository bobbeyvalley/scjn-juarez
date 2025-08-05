scjn_analyzer/
├── main.py                    # Script principal para consola
├── app.py                     # Aplicación Flask para interfaz web
├── requirements.txt           # Dependencias
├── config.py                  # Configuración general
├── 
├── core/
│   ├── __init__.py
│   ├── models.py             # Modelos Pydantic
│   ├── processors.py         # Procesadores de documentos
│   ├── gemini_client.py      # Cliente de Gemini
│   └── utils.py              # Utilidades generales
├── 
├── processors/
│   ├── __init__.py
│   ├── pdf_processor.py      # Procesamiento de PDFs
│   ├── docx_processor.py     # Procesamiento de DOCX/DOC
│   ├── txt_processor.py      # Procesamiento de TXT
│   └── image_processor.py    # OCR para imágenes
├── 
├── templates/                 # Templates HTML para interfaz web
│   ├── index.html
│   ├── upload.html
│   └── results.html
├── 
├── static/                    # CSS, JS para interfaz web
│   ├── css/
│   └── js/
├── 
├── outputs/                   # Carpeta de salidas
│   ├── expedientes/          # Por expediente
│   ├── mapeos/               # JSONs individuales
│   ├── reportes/             # Reportes ejecutivos
│   └── bitacoras/            # Logs de procesamiento
└── 
└── tests/                     # Tests unitarios
    ├── __init__.py
    └── test_processors.py