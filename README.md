# Asistente IA para Agenda de Contactos

Un asistente inteligente que permite consultar información de una agenda de contactos mediante lenguaje natural, con capacidad de mantener contexto entre consultas.

## Características

- **Procesamiento de lenguaje natural**: Entiende consultas en lenguaje natural sobre contactos
- **Manejo de contexto**: Mantiene el contexto de la conversación para preguntas de seguimiento
- **Respuestas naturales**: Genera respuestas en lenguaje natural y conversacional
- **Carga dinámica de datos**: Detecta automáticamente la estructura de los datos
- **Visualización del flujo**: Herramienta para visualizar todo el proceso de consulta
- **Sistema de logs**: Genera logs detallados para análisis posterior

## Estructura del proyecto

```
asistente_ia_agenda/
├── config.py                  # Configuración (API keys)
├── main.py                    # Punto de entrada principal
├── visualizar_flujo_mejorado.py  # Visualizador del flujo de consulta
├── visualizar_flujo_con_logs.py  # Visualizador con sistema de logs
├── prueba_automatizada.py     # Script para pruebas automatizadas
├── datos/                     # Datos de la agenda
│   └── agenda.xlsx            # Archivo Excel con los contactos
├── helpers/                   # Módulos auxiliares
│   ├── dynamic_loader.py      # Carga dinámica de datos
│   ├── enhanced_query.py      # Sistema de consultas mejorado
│   ├── excel_loader.py        # Cargador de archivos Excel
│   └── session_context.py     # Manejo de contexto de sesión
└── logs/                      # Directorio para archivos de log
```

## Requisitos

- Python 3.8 o superior
- Bibliotecas requeridas:
  - google-generativeai
  - pandas
  - openpyxl
  - colorama
  - pyttsx3 (para salida de voz)
  - SpeechRecognition (para entrada de voz)

## Instalación

1. Clona este repositorio:
```
git clone https://github.com/tu-usuario/asistente_ia_agenda.git
cd asistente_ia_agenda
```

2. Instala las dependencias:
```
pip install -r requirements.txt
```

3. Crea un archivo `config.py` con tu clave de API de Google:
```python
GOOGLE_API_KEY = "tu-clave-api-aqui"
```

## Uso

### Modo interactivo básico

```
python main.py
```

### Visualizador de flujo de consulta

```
python visualizar_flujo_mejorado.py
```

### Visualizador con logs detallados

```
python visualizar_flujo_con_logs.py
```

### Pruebas automatizadas

```
python prueba_automatizada.py
```

## Ejemplos de consultas

- "¿Cuál es el teléfono de Juan Pérez?"
- "¿Dónde vive Ana Ramírez?"
- "¿Cuál es el correo electrónico de Carlos Martínez?"
- "¿Quién tiene más de 30 años?"
- "¿Cuántas personas hay en la agenda?"

### Consultas de seguimiento

- "¿Y cuál es su dirección?"
- "¿Qué edad tiene?"
- "¿Cuál es su correo?"

## Arquitectura del sistema

El sistema utiliza un enfoque de dos pasos para procesar consultas:

1. **Extracción de parámetros**: Un primer LLM analiza la consulta y extrae los parámetros relevantes (persona, atributo, etc.)
2. **Búsqueda de datos**: Se realiza una búsqueda directa en los datos usando los parámetros extraídos
3. **Generación de respuesta**: Un segundo LLM genera una respuesta natural basada en los datos encontrados y el contexto

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue para discutir los cambios que te gustaría hacer.

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.
