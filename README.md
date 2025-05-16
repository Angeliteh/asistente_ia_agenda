# Asistente IA para Agenda de Contactos con SQLite

Un asistente inteligente avanzado que permite consultar información de una agenda de contactos mediante lenguaje natural, utilizando SQLite como base de datos y modelos LLM para análisis y generación de respuestas. El sistema mantiene contexto entre consultas, maneja errores ortográficos, nombres parciales y consultas complejas, con búsquedas flexibles y un sistema de caché semántico para respuestas rápidas.

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
1. **Analizar consulta**: Genera una estrategia de búsqueda estructurada y una clave semántica
2. **Generar SQL**: Crea una consulta SQL flexible y optimizada basada en la estrategia
3. **Ejecutar SQL**: Ejecuta la consulta en la base de datos SQLite
4. **Evaluar resultados**: Evalúa los resultados y sugiere refinamientos automáticos
5. **Generar respuesta**: Crea una respuesta natural basada en los resultados

La función `procesar_consulta_completa` centraliza todo el flujo de procesamiento, incluyendo refinamiento automático para consultas sin resultados.

### 4. Sistemas de caché inteligente

#### 4.1 Caché tradicional (`helpers/cache_manager.py`)

Sistema para almacenar y reutilizar resultados de consultas frecuentes:
- Reduce el tiempo de respuesta hasta en un 70%
- Reconoce consultas similares basadas en estrategias de búsqueda
- Persistencia en disco para mantener el caché entre reinicios
- Estadísticas de uso (aciertos, fallos, tasa de aciertos)

#### 4.2 Caché semántico (`helpers/semantic_cache.py`)

Sistema avanzado que utiliza claves semánticas generadas por el LLM para identificar consultas semánticamente equivalentes:

##### 4.2.1 Funcionamiento del caché semántico

El caché semántico funciona en varias etapas:

1. **Normalización de claves**: Cuando se recibe una consulta, se genera una clave semántica normalizada utilizando el LLM.
2. **Verificación de caché**: Se busca la clave normalizada en el caché.
3. **Recuperación o procesamiento**: Si la clave existe en el caché, se devuelve el resultado almacenado. Si no, se procesa la consulta completa.
4. **Almacenamiento**: Después de procesar una consulta, el resultado se almacena en el caché con la clave normalizada.

##### 4.2.2 Normalización de claves semánticas

El proceso de normalización convierte consultas similares en la misma clave semántica:

- **Formato estándar**: Las claves siguen el formato `tipo:entidad:atributo` (ej: `persona:luis_perez:telefono`)
- **Normalización de términos**: Términos similares se convierten a una forma canónica (ej: "teléfono", "celular", "móvil" → "telefono")
- **Normalización de nombres**: Los nombres se normalizan a formato `nombre_apellido` (ej: "Luis Pérez", "Pérez Luis" → "luis_perez")
- **Eliminación de variaciones**: Se eliminan acentos, espacios y caracteres especiales

##### 4.2.3 Configuración y control del caché

El caché semántico puede configurarse y controlarse de varias maneras:

- **Configuración en `config.py`**:
  ```python
  # Configuración del caché
  SEMANTIC_CACHE_ENABLED = True  # Cambiar a False para desactivar el caché semántico
  SEMANTIC_CACHE_MAX_SIZE = 1000  # Tamaño máximo del caché (número de entradas)
  SEMANTIC_CACHE_FILE = os.path.join(DATA_DIR, "semantic_cache.json")  # Ruta del archivo de caché
  ```

- **Desactivación temporal**: Usar el argumento `--no-cache` en `prueba_agenda_unificada.py`:
  ```bash
  python prueba_agenda_unificada.py --escenario 1 --tiempos --no-cache
  ```

- **Limpieza del caché**: Reiniciar el caché para aplicar cambios en la normalización:
  ```python
  from helpers.llm_normalizer import limpiar_cache_normalizacion
  from helpers.semantic_cache import semantic_cache

  # Limpiar caché de normalización
  limpiar_cache_normalizacion()

  # Limpiar caché semántico
  semantic_cache.cache = {}
  ```

##### 4.2.4 Estadísticas del caché

El sistema proporciona estadísticas detalladas sobre el uso del caché:

- **Tamaño actual**: Número de entradas almacenadas en el caché
- **Tamaño máximo**: Capacidad máxima del caché
- **Aciertos (hits)**: Número de consultas recuperadas del caché
- **Fallos (misses)**: Número de consultas que no se encontraron en el caché
- **Tasa de aciertos**: Porcentaje de consultas que se recuperaron del caché
- **Ahorro estimado**: Número de llamadas LLM ahorradas (cada acierto ahorra aproximadamente 3 llamadas LLM)

Para ver las estadísticas del caché:
```bash
python prueba_agenda_unificada.py --escenario 1 --tiempos
```

Al final de la ejecución, se mostrarán estadísticas como:
```
📊 Estadísticas del caché semántico:
   - Tamaño actual: 5 / 1000 entradas
   - Aciertos (hits): 3
   - Fallos (misses): 4
   - Tasa de aciertos: 42.86%
   - Ahorro estimado: 3 consultas = 9 llamadas LLM
```

##### 4.2.5 Ejemplos de normalización

Ejemplos de cómo se normalizan diferentes consultas a la misma clave semántica:

| Consulta original | Clave semántica normalizada |
|-------------------|------------------------------|
| "¿Cuál es el teléfono de Luis Pérez?" | `persona:luis_perez:telefono` |
| "¿Me puedes dar el número de Luis Pérez?" | `persona:luis_perez:telefono` |
| "¿Cuál es el celular de Luis Pérez Ibáñez?" | `persona:luis_perez:telefono` |
| "dame el telefono de luiz perez" | `persona:luis_perez:telefono` |
| "¿Cuál es el correo electrónico de Luis Pérez?" | `persona:luis_perez:correo` |
| "¿Me puedes dar el email de Luis Pérez?" | `persona:luis_perez:correo` |

##### 4.2.6 Ventajas del caché semántico

- **Reducción de costos**: Menos llamadas a la API del LLM
- **Mejora de rendimiento**: Respuestas más rápidas para consultas frecuentes
- **Consistencia**: Respuestas consistentes para consultas similares
- **Flexibilidad**: Reconoce variaciones en la formulación de las consultas
- **Persistencia**: Mantiene el caché entre reinicios del sistema

### 5. Utilidades LLM (`helpers/llm_utils.py`)

Funciones comunes para interactuar con modelos LLM:
- `llamar_llm`: Llama al modelo con fallback automático
- `parsear_respuesta_json`: Procesa respuestas JSON del LLM
- `generar_respuesta_texto`: Genera respuestas de texto simples

### 6. Configuración centralizada

#### 6.1 Configuración general (`config.py`)

Contiene todas las constantes y parámetros del sistema:
- Rutas de archivos
- Configuración de la base de datos
- Parámetros de los modelos LLM
- Límites y umbrales
- Mapeo de atributos

#### 6.2 Configuración de logging (`helpers/logging_config/config.py`)

Sistema flexible para controlar el nivel de detalle en los logs:
- Niveles configurables para consola y archivos
- Ajuste dinámico del nivel de log durante la ejecución
- Persistencia de logs detallados en archivos
- Comandos interactivos para cambiar el nivel de log

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

### Búsqueda y procesamiento
- **Búsquedas SQL flexibles**: Utiliza LIKE con comodines y condiciones OR para mayor flexibilidad
- **Sistema de puntuación**: Clasifica resultados por relevancia usando CASE WHEN
- **Refinamiento automático**: Intenta estrategias alternativas cuando no encuentra resultados
- **Flujo unificado**: Función centralizada para procesar consultas de manera consistente
- **Fallback automático de modelos**: Si Gemini 2.0 Flash falla, recurre a Gemini 1.5 Flash

### Caché y rendimiento
- **Caché tradicional**: Reconoce consultas similares basadas en estrategias de búsqueda
- **Caché semántico**: Identifica consultas semánticamente equivalentes con claves generadas por LLM
- **Control de caché**: Opción para habilitar/deshabilitar el caché semántico según necesidades
- **Estadísticas detalladas**: Información sobre aciertos, fallos y ahorro de llamadas LLM
- **Persistencia en disco**: Mantiene el caché entre reinicios para mejor rendimiento

### Experiencia de usuario
- **Manejo de contexto**: Mantiene historial de consultas y respuestas para referencias pronominales
- **Tolerancia a errores**: Maneja errores ortográficos y nombres parciales
- **Consultas de listado**: Capacidad para listar múltiples registros con formato consistente
- **Consultas combinadas**: Procesa consultas que involucran múltiples personas o condiciones
- **Control de logging**: Ajuste dinámico del nivel de detalle en los logs durante la ejecución

## Uso

### Asistente de línea de comandos

```bash
python asistente_llm_search.py
```

Comandos disponibles durante la ejecución:
- `salir`: Salir del asistente
- `debug`: Activar/desactivar modo debug
- `cache` o `caché`: Mostrar estadísticas del caché
- `logs` o `log`: Mostrar información de logs
- `log level [NIVEL]`: Cambiar nivel de log (DEBUG, INFO, WARNING, ERROR)
- `ayuda` o `help`: Mostrar ayuda de comandos

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

# Desactivar el caché semántico para depuración
python prueba_agenda_unificada.py --no-cache

# Combinar opciones
python prueba_agenda_unificada.py --escenario 3 --tiempos --no-cache
```

### Aplicación Flutter

La aplicación Flutter se encuentra en la carpeta `agenda_assitant/` y se conecta al servidor API para proporcionar una interfaz móvil para el asistente.

Para ejecutar la aplicación Flutter:

1. Asegúrate de que el servidor API esté en ejecución: `python app.py`
2. Actualiza la URL del servidor en `lib/services/api_service.dart` si es necesario
3. Ejecuta la aplicación Flutter desde Android Studio o VS Code
