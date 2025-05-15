# Mejoras Futuras para el Asistente IA de Agenda

Este documento detalla las mejoras propuestas para futuras versiones del Asistente IA para Agenda de Contactos.

## 1. Optimizaciones de código

### 1.1. Función común para llamar al LLM

Actualmente, el código para llamar a los modelos LLM se repite en varias funciones. Se propone crear una función común:

```python
def llamar_llm(prompt, max_output_tokens=None, safety_settings=None):
    """Función común para llamar al LLM con fallback automático.
    
    Args:
        prompt (str): El prompt a enviar al modelo
        max_output_tokens (int, optional): Límite de tokens de salida
        safety_settings (list, optional): Configuración de seguridad
        
    Returns:
        object: Respuesta del modelo
    """
    try:
        modelo = genai.GenerativeModel(model_name="gemini-2.0-flash")
        
        # Configurar el modelo para evitar repeticiones y respuestas más coherentes
        generation_config = {
            "temperature": 0.2,  # Más determinista
            "top_p": 0.95,
            "top_k": 40,
        }
        if max_output_tokens:
            generation_config["max_output_tokens"] = max_output_tokens
        
        respuesta = modelo.generate_content(
            prompt, 
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        print(f"{Fore.GREEN}✓ Usando modelo: gemini-2.0-flash{Style.RESET_ALL}")
        return respuesta
    except Exception as e:
        print(f"{Fore.YELLOW}⚠ Error con gemini-2.0-flash: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⚠ Intentando con modelo alternativo: gemini-1.5-flash{Style.RESET_ALL}")
        
        modelo = genai.GenerativeModel(model_name="gemini-1.5-flash")
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 40,
        }
        if max_output_tokens:
            generation_config["max_output_tokens"] = min(max_output_tokens, 1024)
        
        respuesta = modelo.generate_content(
            prompt, 
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        print(f"{Fore.GREEN}✓ Usando modelo: gemini-1.5-flash{Style.RESET_ALL}")
        return respuesta
```

### 1.2. Función común para parsear respuestas JSON

El código para limpiar y parsear respuestas JSON también se repite. Se propone crear una función común:

```python
def parsear_respuesta_json(respuesta):
    """Función común para parsear respuestas JSON del LLM.
    
    Args:
        respuesta (object): Respuesta del modelo
        
    Returns:
        dict: Objeto JSON parseado
    """
    try:
        texto_respuesta = respuesta.text.strip()
        if "```json" in texto_respuesta:
            texto_respuesta = texto_respuesta.split("```json")[1].split("```")[0].strip()
        elif "```" in texto_respuesta:
            texto_respuesta = texto_respuesta.split("```")[1].strip()
        
        return json.loads(texto_respuesta)
    except Exception as e:
        print(f"Error al parsear respuesta JSON: {e}")
        print(f"Respuesta recibida: {respuesta.text}")
        return {
            "error": str(e),
            "respuesta_original": respuesta.text
        }
```

### 1.3. Optimización de vista previa de la base de datos

Actualmente, la función `obtener_vista_previa_db` se llama en varias funciones. Se propone obtener la vista previa una sola vez y pasarla como parámetro:

```python
def flujo_completo(consulta, contexto=None, db_path="datos/agenda.db"):
    """Función que ejecuta el flujo completo de análisis y respuesta.
    
    Args:
        consulta (str): Consulta del usuario
        contexto (dict, optional): Contexto de la conversación
        db_path (str): Ruta a la base de datos SQLite
        
    Returns:
        str: Respuesta generada
    """
    # Obtener vista previa de la base de datos una sola vez
    vista_previa = obtener_vista_previa_db(db_path)
    
    # Paso 1: Analizar consulta
    estrategia = analizar_consulta(consulta, contexto, vista_previa)
    
    # Paso 2: Generar SQL
    consulta_sql = generar_sql_desde_estrategia(estrategia, vista_previa)
    
    # Paso 3: Ejecutar consulta SQL
    resultado_sql = ejecutar_consulta_llm(consulta_sql["consulta"], consulta_sql["parametros"], db_path)
    
    # Paso 4: Evaluar resultados
    evaluacion = evaluar_resultados(consulta, resultado_sql, estrategia, vista_previa)
    
    # Paso 5: Generar respuesta
    respuesta = generar_respuesta_desde_resultados(consulta, resultado_sql, estrategia, evaluacion, vista_previa)
    
    return respuesta
```

## 2. Mejoras de funcionalidad

### 2.1. Refinamiento automático de consultas

Implementar un sistema que ejecute automáticamente la "nueva_estrategia" sugerida en la evaluación cuando los resultados no son satisfactorios:

```python
def flujo_completo_con_refinamiento(consulta, contexto=None, db_path="datos/agenda.db", max_refinamientos=2):
    """Función que ejecuta el flujo completo con refinamiento automático.
    
    Args:
        consulta (str): Consulta del usuario
        contexto (dict, optional): Contexto de la conversación
        db_path (str): Ruta a la base de datos SQLite
        max_refinamientos (int): Número máximo de refinamientos
        
    Returns:
        str: Respuesta generada
    """
    vista_previa = obtener_vista_previa_db(db_path)
    estrategia = analizar_consulta(consulta, contexto, vista_previa)
    
    for i in range(max_refinamientos + 1):
        consulta_sql = generar_sql_desde_estrategia(estrategia, vista_previa)
        resultado_sql = ejecutar_consulta_llm(consulta_sql["consulta"], consulta_sql["parametros"], db_path)
        evaluacion = evaluar_resultados(consulta, resultado_sql, estrategia, vista_previa)
        
        # Si los resultados son satisfactorios o no hay sugerencia de refinamiento, terminar
        if evaluacion.get("satisfactorio", False) or not evaluacion.get("refinamiento", {}).get("nueva_estrategia"):
            break
            
        # Refinar la estrategia y continuar
        estrategia = evaluacion["refinamiento"]["nueva_estrategia"]
        print(f"{Fore.YELLOW}⚠ Refinando consulta (intento {i+1}/{max_refinamientos})...{Style.RESET_ALL}")
    
    # Generar respuesta con los mejores resultados obtenidos
    respuesta = generar_respuesta_desde_resultados(consulta, resultado_sql, estrategia, evaluacion, vista_previa)
    return respuesta
```

### 2.2. Caché de consultas frecuentes

Implementar un sistema de caché para consultas frecuentes:

```python
class ConsultaCache:
    """Clase para cachear consultas frecuentes."""
    
    def __init__(self, max_size=100):
        """Inicializa el caché.
        
        Args:
            max_size (int): Tamaño máximo del caché
        """
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, consulta):
        """Obtiene una respuesta del caché.
        
        Args:
            consulta (str): Consulta normalizada
            
        Returns:
            dict: Respuesta cacheada o None
        """
        if consulta in self.cache:
            self.hits += 1
            return self.cache[consulta]
        self.misses += 1
        return None
    
    def set(self, consulta, respuesta):
        """Guarda una respuesta en el caché.
        
        Args:
            consulta (str): Consulta normalizada
            respuesta (dict): Respuesta a cachear
        """
        if len(self.cache) >= self.max_size:
            # Eliminar la entrada más antigua
            self.cache.pop(next(iter(self.cache)))
        self.cache[consulta] = respuesta
    
    def normalizar_consulta(self, consulta):
        """Normaliza una consulta para el caché.
        
        Args:
            consulta (str): Consulta original
            
        Returns:
            str: Consulta normalizada
        """
        # Eliminar espacios extra, convertir a minúsculas, etc.
        return " ".join(consulta.lower().split())
    
    def estadisticas(self):
        """Devuelve estadísticas del caché.
        
        Returns:
            dict: Estadísticas del caché
        """
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            "tamaño": len(self.cache),
            "max_tamaño": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }
```

## 3. Mejoras de interfaz de usuario

### 3.1. Interfaz web con Flask

Implementar una interfaz web simple con Flask:

```python
from flask import Flask, render_template, request, jsonify
from helpers.llm_search import flujo_completo

app = Flask(__name__)
contexto_global = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/consulta', methods=['POST'])
def consulta():
    global contexto_global
    consulta = request.json.get('consulta', '')
    
    if not consulta:
        return jsonify({"error": "Consulta vacía"})
    
    respuesta = flujo_completo(consulta, contexto_global)
    contexto_global = {
        "consulta_anterior": consulta,
        "respuesta_anterior": respuesta,
        "historial_consultas": contexto_global.get("historial_consultas", []) + [consulta],
        "historial_respuestas": contexto_global.get("historial_respuestas", []) + [respuesta]
    }
    
    return jsonify({"respuesta": respuesta})

if __name__ == '__main__':
    app.run(debug=True)
```

### 3.2. Interfaz de línea de comandos mejorada

Implementar una interfaz de línea de comandos más interactiva:

```python
import cmd
import colorama
from colorama import Fore, Style
from helpers.llm_search import flujo_completo

colorama.init()

class AsistenteShell(cmd.Cmd):
    """Shell interactivo para el asistente de agenda."""
    
    intro = f"{Fore.GREEN}Bienvenido al Asistente IA para Agenda. Escribe 'ayuda' para ver los comandos disponibles.{Style.RESET_ALL}"
    prompt = f"{Fore.BLUE}agenda> {Style.RESET_ALL}"
    
    def __init__(self):
        super().__init__()
        self.contexto = {}
    
    def default(self, line):
        """Procesa cualquier línea que no sea un comando como una consulta."""
        if line:
            respuesta = flujo_completo(line, self.contexto)
            print(f"\n{Fore.GREEN}🤖 {respuesta}{Style.RESET_ALL}\n")
            
            # Actualizar contexto
            self.contexto = {
                "consulta_anterior": line,
                "respuesta_anterior": respuesta,
                "historial_consultas": self.contexto.get("historial_consultas", []) + [line],
                "historial_respuestas": self.contexto.get("historial_respuestas", []) + [respuesta]
            }
    
    def do_limpiar(self, arg):
        """Limpia el contexto de la conversación."""
        self.contexto = {}
        print(f"{Fore.YELLOW}Contexto limpiado.{Style.RESET_ALL}")
    
    def do_salir(self, arg):
        """Sale del programa."""
        print(f"{Fore.GREEN}¡Hasta luego!{Style.RESET_ALL}")
        return True
    
    def do_ayuda(self, arg):
        """Muestra la ayuda."""
        print(f"\n{Fore.YELLOW}Comandos disponibles:{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}limpiar{Style.RESET_ALL} - Limpia el contexto de la conversación")
        print(f"  {Fore.CYAN}salir{Style.RESET_ALL} - Sale del programa")
        print(f"  {Fore.CYAN}ayuda{Style.RESET_ALL} - Muestra esta ayuda")
        print(f"\n{Fore.YELLOW}Para hacer una consulta, simplemente escríbela y presiona Enter.{Style.RESET_ALL}\n")

if __name__ == '__main__':
    AsistenteShell().cmdloop()
```

## 4. Mejoras de rendimiento y escalabilidad

### 4.1. Paralelización de consultas

Implementar paralelización para procesar múltiples consultas simultáneamente:

```python
import concurrent.futures

def procesar_consultas_en_paralelo(consultas, contextos=None, max_workers=4):
    """Procesa múltiples consultas en paralelo.
    
    Args:
        consultas (list): Lista de consultas
        contextos (list, optional): Lista de contextos correspondientes
        max_workers (int): Número máximo de workers
        
    Returns:
        list: Lista de respuestas
    """
    if contextos is None:
        contextos = [None] * len(consultas)
    
    resultados = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Crear un futuro para cada consulta
        futuros = {executor.submit(flujo_completo, consulta, contexto): i 
                  for i, (consulta, contexto) in enumerate(zip(consultas, contextos))}
        
        # Procesar los resultados a medida que se completan
        for futuro in concurrent.futures.as_completed(futuros):
            indice = futuros[futuro]
            try:
                resultado = futuro.result()
                resultados.append((indice, resultado))
            except Exception as e:
                resultados.append((indice, f"Error: {str(e)}"))
    
    # Ordenar los resultados por índice
    resultados.sort(key=lambda x: x[0])
    return [r[1] for r in resultados]
```

### 4.2. Optimización de consultas SQL

Implementar un sistema para optimizar consultas SQL frecuentes:

```python
def optimizar_consulta_sql(consulta_sql):
    """Optimiza una consulta SQL.
    
    Args:
        consulta_sql (str): Consulta SQL original
        
    Returns:
        str: Consulta SQL optimizada
    """
    # Eliminar columnas innecesarias en consultas de conteo
    if "COUNT(*)" in consulta_sql and "SELECT *" in consulta_sql:
        consulta_sql = consulta_sql.replace("SELECT *", "SELECT COUNT(*)")
        # Eliminar ORDER BY en consultas de conteo
        if "ORDER BY" in consulta_sql:
            consulta_sql = consulta_sql.split("ORDER BY")[0]
    
    # Añadir índices para consultas frecuentes
    if "WHERE nombre_completo" in consulta_sql:
        # Asegurarse de que existe un índice en nombre_completo
        pass
    
    return consulta_sql
```

## 5. Integración con otras tecnologías

### 5.1. Integración con servicios de voz

Implementar integración con servicios de voz para entrada y salida:

```python
from google.cloud import texttospeech
import speech_recognition as sr

def texto_a_voz(texto):
    """Convierte texto a voz.
    
    Args:
        texto (str): Texto a convertir
        
    Returns:
        bytes: Audio en formato MP3
    """
    cliente = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=texto)
    
    voz = texttospeech.VoiceSelectionParams(
        language_code="es-ES",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    
    config_audio = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    respuesta = cliente.synthesize_speech(
        input=input_text, voice=voz, audio_config=config_audio
    )
    
    return respuesta.audio_content

def voz_a_texto():
    """Convierte voz a texto.
    
    Returns:
        str: Texto reconocido
    """
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Escuchando...")
        audio = recognizer.listen(source)
    
    try:
        texto = recognizer.recognize_google(audio, language="es-ES")
        return texto
    except sr.UnknownValueError:
        return "No se pudo entender el audio"
    except sr.RequestError:
        return "Error en el servicio de reconocimiento de voz"
```

### 5.2. Integración con bases de datos externas

Implementar integración con otras bases de datos:

```python
def conectar_base_datos(tipo, **kwargs):
    """Conecta a diferentes tipos de bases de datos.
    
    Args:
        tipo (str): Tipo de base de datos ('sqlite', 'mysql', 'postgresql')
        **kwargs: Parámetros de conexión
        
    Returns:
        object: Conexión a la base de datos
    """
    if tipo == 'sqlite':
        import sqlite3
        return sqlite3.connect(kwargs.get('db_path', 'datos/agenda.db'))
    elif tipo == 'mysql':
        import mysql.connector
        return mysql.connector.connect(
            host=kwargs.get('host', 'localhost'),
            user=kwargs.get('user', 'root'),
            password=kwargs.get('password', ''),
            database=kwargs.get('database', 'agenda')
        )
    elif tipo == 'postgresql':
        import psycopg2
        return psycopg2.connect(
            host=kwargs.get('host', 'localhost'),
            user=kwargs.get('user', 'postgres'),
            password=kwargs.get('password', ''),
            dbname=kwargs.get('dbname', 'agenda')
        )
    else:
        raise ValueError(f"Tipo de base de datos no soportado: {tipo}")
```

## 6. Seguridad y privacidad

### 6.1. Cifrado de datos sensibles

Implementar cifrado para datos sensibles:

```python
from cryptography.fernet import Fernet

class GestorCifrado:
    """Gestor de cifrado para datos sensibles."""
    
    def __init__(self, clave=None):
        """Inicializa el gestor de cifrado.
        
        Args:
            clave (bytes, optional): Clave de cifrado
        """
        if clave is None:
            clave = Fernet.generate_key()
        self.cipher_suite = Fernet(clave)
    
    def cifrar(self, datos):
        """Cifra datos.
        
        Args:
            datos (str): Datos a cifrar
            
        Returns:
            bytes: Datos cifrados
        """
        return self.cipher_suite.encrypt(datos.encode())
    
    def descifrar(self, datos_cifrados):
        """Descifra datos.
        
        Args:
            datos_cifrados (bytes): Datos cifrados
            
        Returns:
            str: Datos descifrados
        """
        return self.cipher_suite.decrypt(datos_cifrados).decode()
```

### 6.2. Autenticación de usuarios

Implementar autenticación básica:

```python
import hashlib
import os

class GestorUsuarios:
    """Gestor de usuarios para autenticación."""
    
    def __init__(self, archivo_usuarios="datos/usuarios.json"):
        """Inicializa el gestor de usuarios.
        
        Args:
            archivo_usuarios (str): Ruta al archivo de usuarios
        """
        self.archivo_usuarios = archivo_usuarios
        self.usuarios = self._cargar_usuarios()
    
    def _cargar_usuarios(self):
        """Carga los usuarios desde el archivo.
        
        Returns:
            dict: Diccionario de usuarios
        """
        if os.path.exists(self.archivo_usuarios):
            with open(self.archivo_usuarios, 'r') as f:
                return json.load(f)
        return {}
    
    def _guardar_usuarios(self):
        """Guarda los usuarios en el archivo."""
        with open(self.archivo_usuarios, 'w') as f:
            json.dump(self.usuarios, f)
    
    def _hash_password(self, password, salt=None):
        """Genera un hash para una contraseña.
        
        Args:
            password (str): Contraseña
            salt (bytes, optional): Salt para el hash
            
        Returns:
            tuple: (hash, salt)
        """
        if salt is None:
            salt = os.urandom(32)
        hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return hash.hex(), salt.hex()
    
    def registrar_usuario(self, username, password):
        """Registra un nuevo usuario.
        
        Args:
            username (str): Nombre de usuario
            password (str): Contraseña
            
        Returns:
            bool: True si se registró correctamente
        """
        if username in self.usuarios:
            return False
        
        hash, salt = self._hash_password(password)
        self.usuarios[username] = {
            'hash': hash,
            'salt': salt
        }
        self._guardar_usuarios()
        return True
    
    def verificar_usuario(self, username, password):
        """Verifica las credenciales de un usuario.
        
        Args:
            username (str): Nombre de usuario
            password (str): Contraseña
            
        Returns:
            bool: True si las credenciales son correctas
        """
        if username not in self.usuarios:
            return False
        
        usuario = self.usuarios[username]
        salt = bytes.fromhex(usuario['salt'])
        hash_almacenado = usuario['hash']
        hash_calculado, _ = self._hash_password(password, salt)
        
        return hash_calculado == hash_almacenado
```
