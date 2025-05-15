# Asistente IA para Agenda de Contactos con SQLite

Un asistente inteligente avanzado que permite consultar información de una agenda de contactos mediante lenguaje natural, utilizando SQLite como base de datos y modelos LLM para análisis y generación de respuestas. El sistema mantiene contexto entre consultas, maneja errores ortográficos, nombres parciales y consultas complejas.

## Estructura del proyecto

```
asistente_ia_agenda/
├── app.py                      # Servidor API para la app Flutter
├── asistente_llm_search.py     # Asistente de línea de comandos
├── config.py                   # Configuración centralizada
├── pre_entrenar_cache.py       # Script para pre-entrenar el caché
├── prueba_agenda_unificada.py  # Script de prueba principal
├── datos/                      # Datos de la agenda
│   ├── agenda.db               # Base de datos SQLite
│   ├── cache.json              # Caché de consultas frecuentes
│   └── agenda.xlsx             # Archivo Excel original (opcional)
├── helpers/                    # Módulos auxiliares
│   ├── agenda_real_mapper.py   # Carga datos de Excel a SQLite
│   ├── cache_manager.py        # Gestión del caché inteligente
│   ├── llm_search.py           # Lógica principal del sistema de búsqueda
│   ├── llm_utils.py            # Utilidades para LLM (llamadas, parseo)
│   └── sqlite_adapter.py       # Interacción con la base de datos SQLite
└── agenda_assitant/            # Aplicación Flutter
    └── lib/                    # Código fuente de la app Flutter
```

## Componentes principales

### 1. Asistente de línea de comandos (`asistente_llm_search.py`)

Interfaz de línea de comandos para interactuar con el asistente. Características:
- Interfaz conversacional con efectos de tipeo
- Modo debug para ver detalles del proceso
- Creación automática de la base de datos si no existe
- Estadísticas de uso del caché

### 2. Servidor API (`app.py`)

Servidor Flask que expone la funcionalidad del asistente a través de endpoints REST:
- `/api/query` - Procesa consultas y devuelve respuestas
- `/api/health` - Verifica el estado del servidor
- `/api/reset` - Reinicia el contexto de conversación
- `/api/context` - Obtiene el contexto actual
- `/api/cache` - Obtiene información del caché
- `/api/cache/clear` - Limpia el caché

### 3. Lógica principal (`helpers/llm_search.py`)

Implementa el enfoque de 5 pasos para procesar consultas:
1. **Analizar consulta**: Genera una estrategia de búsqueda estructurada
2. **Generar SQL**: Crea una consulta SQL optimizada basada en la estrategia
3. **Ejecutar SQL**: Ejecuta la consulta en la base de datos SQLite
4. **Evaluar resultados**: Evalúa los resultados y sugiere refinamientos
5. **Generar respuesta**: Crea una respuesta natural basada en los resultados

La función `procesar_consulta_completa` centraliza todo el flujo de procesamiento.

### 4. Sistema de caché inteligente (`helpers/cache_manager.py`)

Sistema para almacenar y reutilizar resultados de consultas frecuentes:
- Reduce el tiempo de respuesta hasta en un 70%
- Reconoce consultas similares aunque estén formuladas de manera diferente
- Persistencia en disco para mantener el caché entre reinicios
- Estadísticas de uso (aciertos, fallos, tasa de aciertos)

### 5. Utilidades LLM (`helpers/llm_utils.py`)

Funciones comunes para interactuar con modelos LLM:
- `llamar_llm`: Llama al modelo con fallback automático
- `parsear_respuesta_json`: Procesa respuestas JSON del LLM
- `generar_respuesta_texto`: Genera respuestas de texto simples

### 6. Configuración centralizada (`config.py`)

Contiene todas las constantes y parámetros del sistema:
- Rutas de archivos
- Configuración de la base de datos
- Parámetros de los modelos LLM
- Límites y umbrales
- Mapeo de atributos

### 7. Script de pre-entrenamiento (`pre_entrenar_cache.py`)

Script para pre-entrenar el caché con consultas comunes:
- Procesa automáticamente consultas frecuentes
- Reduce el tiempo de respuesta para usuarios reales
- Opciones para limpiar el caché y mostrar respuestas

## Flujo del sistema

El sistema sigue un flujo optimizado para procesar consultas:

1. **Verificación de caché**:
   - Recibe: Consulta en lenguaje natural
   - Proceso: Analiza la consulta y verifica si hay un resultado en caché
   - Si hay coincidencia: Devuelve el resultado inmediatamente (1 llamada LLM)
   - Si no hay coincidencia: Continúa con el flujo completo (4 llamadas LLM)

2. **Análisis de la consulta**:
   - Recibe: Consulta en lenguaje natural + contexto anterior
   - Proceso: Analiza la consulta y genera una estrategia de búsqueda
   - Salida: Estrategia estructurada en formato JSON

3. **Generación de SQL**:
   - Recibe: Estrategia de búsqueda
   - Proceso: Genera una consulta SQL optimizada
   - Salida: Consulta SQL con parámetros y explicación

4. **Ejecución de SQL**:
   - Recibe: Consulta SQL + parámetros
   - Proceso: Ejecuta la consulta en la base de datos SQLite
   - Salida: Resultados de la consulta

5. **Evaluación de resultados**:
   - Recibe: Consulta original + resultados + estrategia
   - Proceso: Evalúa si los resultados satisfacen la consulta
   - Salida: Evaluación con posibles refinamientos

6. **Generación de respuesta**:
   - Recibe: Consulta original + resultados + estrategia + evaluación
   - Proceso: Genera una respuesta natural basada en los resultados
   - Salida: Respuesta en lenguaje natural

7. **Almacenamiento en caché**:
   - Guarda el resultado en el caché para futuras consultas similares
   - Actualiza las estadísticas del caché

## Características avanzadas

- **Sistema de caché inteligente**: Reconoce consultas similares y reduce el tiempo de respuesta
- **Flujo unificado**: Función centralizada para procesar consultas de manera consistente
- **Fallback automático de modelos**: Si Gemini 2.0 Flash falla, recurre a Gemini 1.5 Flash
- **Manejo de contexto**: Mantiene historial de consultas y respuestas para referencias pronominales
- **Tolerancia a errores**: Maneja errores ortográficos y nombres parciales
- **Consultas de listado**: Capacidad para listar múltiples registros con formato consistente
- **Evaluación y refinamiento**: Evalúa los resultados y sugiere refinamientos si es necesario

## Uso

### Asistente de línea de comandos

```bash
python asistente_llm_search.py
```

### Pre-entrenamiento del caché

```bash
# Pre-entrenar con todas las consultas predefinidas
python pre_entrenar_cache.py

# Pre-entrenar con una consulta específica
python pre_entrenar_cache.py --consulta "¿Quién es Luis Pérez?"

# Limpiar el caché antes de pre-entrenar
python pre_entrenar_cache.py --limpiar

# Mostrar las respuestas generadas
python pre_entrenar_cache.py --mostrar
```

### Servidor API

```bash
python app.py
```

### Pruebas

```bash
# Ejecutar todos los escenarios
python prueba_agenda_unificada.py

# Ejecutar un escenario específico
python prueba_agenda_unificada.py --escenario 3

# Ejecutar una consulta específica
python prueba_agenda_unificada.py --consulta "¿Quién es Luis Pérez?"

# Mostrar tiempos de ejecución
python prueba_agenda_unificada.py --tiempos
```

### Aplicación Flutter

La aplicación Flutter se encuentra en la carpeta `agenda_assitant/` y se conecta al servidor API para proporcionar una interfaz móvil para el asistente.

Para ejecutar la aplicación Flutter:

1. Asegúrate de que el servidor API esté en ejecución: `python app.py`
2. Actualiza la URL del servidor en `lib/services/api_service.dart` si es necesario
3. Ejecuta la aplicación Flutter desde Android Studio o VS Code
