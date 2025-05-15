# Plan de Adaptabilidad para el Asistente de Agenda

Este documento detalla el plan para transformar el Asistente de Agenda actual en un sistema más adaptable que pueda funcionar con diferentes conjuntos de datos sin necesidad de modificar el código base.

## Objetivo

Crear un sistema que permita:
1. Usar cualquier archivo Excel como fuente de datos
2. Configurar fácilmente nuevos proyectos
3. Adaptar automáticamente los prompts y consultas a la estructura de los datos
4. Mantener todas las funcionalidades actuales (caché, contexto, etc.)

## Fases de Implementación

### Fase 1: Refactorización (2-3 semanas)

**Objetivo**: Separar la lógica específica de la agenda de la lógica general del asistente.

#### Tareas:

1. **Crear interfaces claras entre componentes**
   - [ ] Definir interfaces para cada componente principal
   - [ ] Documentar las entradas y salidas de cada función
   - [ ] Identificar y eliminar dependencias innecesarias

2. **Separar la lógica específica de la agenda**
   - [ ] Crear un módulo `domain/agenda` para la lógica específica de la agenda
   - [ ] Mover las funciones específicas de la agenda a este módulo
   - [ ] Crear adaptadores para conectar con la lógica general

3. **Mejorar la estructura del proyecto**
   - [ ] Reorganizar archivos en carpetas más lógicas:
     - `core/`: Lógica central del asistente
     - `adapters/`: Adaptadores para diferentes fuentes de datos
     - `domain/`: Lógica específica de dominio
     - `interfaces/`: Interfaces de usuario (CLI, API)
     - `utils/`: Utilidades generales

4. **Mejorar la documentación**
   - [ ] Actualizar docstrings en todas las funciones
   - [ ] Crear diagramas de flujo y arquitectura
   - [ ] Actualizar el README con la nueva estructura

### Fase 2: Sistema de Mapeo Dinámico (3-4 semanas)

**Objetivo**: Permitir que el sistema funcione con cualquier estructura de Excel sin modificar el código.

#### Tareas:

1. **Crear analizador de Excel**
   - [ ] Implementar función para analizar la estructura de un Excel
   - [ ] Detectar automáticamente tipos de datos
   - [ ] Identificar posibles columnas clave (nombres, IDs, etc.)
   - [ ] Generar un informe de análisis

2. **Implementar sistema de mapeo configurable**
   - [ ] Crear estructura para definir mapeos entre Excel y SQLite
   - [ ] Implementar validación de mapeos
   - [ ] Crear funciones para aplicar mapeos automáticamente

3. **Generar esquema SQLite dinámico**
   - [ ] Implementar generación de esquema SQLite basado en mapeo
   - [ ] Crear índices automáticamente para columnas clave
   - [ ] Implementar migración de datos cuando cambia el esquema

4. **Crear asistente de mapeo**
   - [ ] Implementar función para sugerir mapeos basados en el análisis
   - [ ] Crear interfaz para ajustar mapeos sugeridos
   - [ ] Implementar validación y pruebas de mapeo

### Fase 3: Configuración por Proyecto (2-3 semanas)

**Objetivo**: Permitir tener diferentes configuraciones para diferentes conjuntos de datos.

#### Tareas:

1. **Diseñar sistema de proyectos**
   - [ ] Definir estructura de carpetas para proyectos
   - [ ] Crear formato para archivos de configuración de proyecto
   - [ ] Implementar carga dinámica de configuración

2. **Implementar configuración por proyecto**
   - [ ] Crear clase `ProjectConfig` para manejar configuración
   - [ ] Implementar carga y validación de configuración
   - [ ] Crear configuraciones predeterminadas para nuevos proyectos

3. **Adaptar código existente**
   - [ ] Modificar `config.py` para usar configuración de proyecto
   - [ ] Actualizar funciones para usar parámetros de proyecto
   - [ ] Implementar selección de proyecto activo

4. **Crear ejemplos de proyectos**
   - [ ] Convertir proyecto actual a nuevo formato
   - [ ] Crear 2-3 ejemplos con diferentes estructuras de datos
   - [ ] Documentar proceso de creación de proyectos

### Fase 4: Prompts Adaptables (2-3 semanas)

**Objetivo**: Hacer que los prompts para el LLM se adapten automáticamente a la estructura de los datos.

#### Tareas:

1. **Crear sistema de templates**
   - [ ] Diseñar formato para templates de prompts
   - [ ] Implementar sistema de placeholders para información dinámica
   - [ ] Crear templates para cada tipo de prompt (análisis, SQL, etc.)

2. **Implementar generación de ejemplos**
   - [ ] Crear función para extraer ejemplos representativos de los datos
   - [ ] Implementar generación de ejemplos de consultas y respuestas
   - [ ] Integrar ejemplos en los templates de prompts

3. **Personalización de prompts**
   - [ ] Permitir personalización de prompts por proyecto
   - [ ] Implementar sistema de versiones de prompts
   - [ ] Crear interfaz para editar y probar prompts

4. **Optimización de prompts**
   - [ ] Implementar métricas para evaluar calidad de prompts
   - [ ] Crear sistema para A/B testing de diferentes prompts
   - [ ] Documentar mejores prácticas para prompts

### Fase 5: Abstracción de Fuente de Datos (2-3 semanas)

**Objetivo**: Separar completamente la lógica del asistente de la fuente de datos específica.

#### Tareas:

1. **Diseñar capa de abstracción**
   - [ ] Crear interfaz `DataSource` para fuentes de datos
   - [ ] Definir métodos estándar para búsqueda y manipulación
   - [ ] Implementar manejo de errores consistente

2. **Implementar adaptadores**
   - [ ] Crear `SQLiteDataSource` para bases SQLite
   - [ ] Implementar `ExcelDataSource` para acceso directo a Excel
   - [ ] Crear `APIDataSource` para fuentes de datos externas

3. **Integrar con lógica existente**
   - [ ] Modificar `llm_search.py` para usar la capa de abstracción
   - [ ] Actualizar generación de SQL para diferentes fuentes
   - [ ] Implementar selección dinámica de fuente de datos

4. **Pruebas con diferentes fuentes**
   - [ ] Crear pruebas para cada tipo de fuente de datos
   - [ ] Verificar consistencia de resultados entre fuentes
   - [ ] Documentar limitaciones y diferencias

### Fase 6: Interfaz de Configuración (3-4 semanas)

**Objetivo**: Facilitar la creación de nuevos proyectos sin necesidad de programar.

#### Tareas:

1. **Diseñar interfaz web simple**
   - [ ] Crear wireframes para la interfaz
   - [ ] Implementar servidor web básico (Flask)
   - [ ] Diseñar flujo de usuario para configuración

2. **Implementar asistentes**
   - [ ] Crear asistente para cargar y analizar Excel
   - [ ] Implementar asistente para configurar mapeo
   - [ ] Crear asistente para personalizar prompts
   - [ ] Implementar asistente para pre-entrenar caché

3. **Generación automática de configuración**
   - [ ] Implementar generación de archivos de configuración
   - [ ] Crear scripts para inicializar nuevos proyectos
   - [ ] Implementar validación de configuración generada

4. **Documentación y tutoriales**
   - [ ] Crear guía paso a paso para nuevos proyectos
   - [ ] Implementar ejemplos interactivos
   - [ ] Crear videos tutoriales

## Cronograma Estimado

| Fase | Duración | Dependencias |
|------|----------|--------------|
| 1. Refactorización | 2-3 semanas | Ninguna |
| 2. Mapeo Dinámico | 3-4 semanas | Fase 1 |
| 3. Configuración por Proyecto | 2-3 semanas | Fase 1 |
| 4. Prompts Adaptables | 2-3 semanas | Fase 3 |
| 5. Abstracción de Fuente de Datos | 2-3 semanas | Fase 1 |
| 6. Interfaz de Configuración | 3-4 semanas | Fases 2, 3, 4, 5 |

**Tiempo total estimado**: 14-20 semanas (3.5-5 meses)

## Hitos y Entregables

### Hito 1: Arquitectura Modular (Fin de Fase 1)
- Código refactorizado con interfaces claras
- Documentación actualizada
- Pruebas unitarias para componentes principales

### Hito 2: Soporte Multi-Estructura (Fin de Fase 2 y 3)
- Sistema capaz de trabajar con diferentes estructuras de Excel
- Configuración por proyecto implementada
- Ejemplos de proyectos con diferentes estructuras

### Hito 3: Adaptabilidad Completa (Fin de Fase 4 y 5)
- Prompts que se adaptan automáticamente a los datos
- Soporte para diferentes fuentes de datos
- Sistema completo funcionando con múltiples conjuntos de datos

### Hito 4: Usabilidad para No Programadores (Fin de Fase 6)
- Interfaz web para configuración
- Asistentes para todas las tareas principales
- Documentación y tutoriales completos

## Próximos Pasos Inmediatos

1. Comenzar con la refactorización del código actual
2. Crear interfaces claras entre componentes
3. Separar la lógica específica de la agenda
4. Mejorar la documentación

## Notas Adicionales

- Mantener compatibilidad con el sistema actual durante todo el proceso
- Implementar pruebas automatizadas para cada componente
- Documentar cada fase a medida que se completa
- Considerar feedback de usuarios durante el desarrollo
