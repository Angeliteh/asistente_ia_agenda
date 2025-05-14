# main.py
# Sistema centralizado de carga de datos y consultas
from helpers.excel_loader import cargar_agenda_excel  # Para compatibilidad
from helpers.dynamic_loader import cargar_agenda_dinamica
from helpers.enhanced_query import process_query
from config import GOOGLE_API_KEY
import google.generativeai as genai
import speech_recognition as sr
import pyttsx3
import os
import pickle

# Configurar clave de API
genai.configure(api_key=GOOGLE_API_KEY)

# Definir archivo de datos
DATOS_FILE = "datos/agenda.xlsx"

# Función para cargar datos de manera dinámica
def cargar_datos(ruta_excel=DATOS_FILE):
    """Carga datos desde Excel de manera dinámica"""
    # Intentar cargar con el cargador dinámico
    resultado = cargar_agenda_dinamica(ruta_excel)

    if resultado["error"]:
        print(f"Error al cargar datos dinámicamente: {resultado['error']}")
        print("Intentando con el cargador tradicional...")
        # Fallback al cargador tradicional
        try:
            registros = cargar_agenda_excel(ruta_excel)
            return {
                "registros": registros,
                "esquema": {},
                "mapeo_columnas": {},
                "error": None
            }
        except Exception as e:
            print(f"Error al cargar datos: {e}")
            return {"registros": [], "esquema": {}, "mapeo_columnas": {}, "error": str(e)}

    return resultado

# Cargar datos al inicio
datos_cargados = cargar_datos()
registros = datos_cargados["registros"]
esquema = datos_cargados["esquema"]
mapeo_columnas = datos_cargados["mapeo_columnas"]

# Mostrar información sobre los datos cargados para verificación
print("\n" + "=" * 50)
print("VERIFICACIÓN DE CARGA DE DATOS")
print("=" * 50)
print(f"📊 Datos cargados: {len(registros)} registros")

# Mostrar esquema detectado
if esquema:
    print(f"\n📋 Esquema detectado: {len(esquema)} columnas")
    for columna, info in esquema.items():
        nombre_original = mapeo_columnas.get(columna, columna)
        print(f"  - {nombre_original} → {columna}: {info['tipo_datos']} ({info['categoria']})")

# Mostrar el primer registro como ejemplo
if registros and len(registros) > 0:
    print("\n📝 Ejemplo (primer registro):")
    for columna, valor in registros[0].items():
        nombre_original = mapeo_columnas.get(columna, columna)
        print(f"  - {nombre_original}: {valor}")

print("=" * 50)
input("\nPresiona Enter para continuar con el asistente...")

# Archivo para guardar preferencias
PREFERENCIAS_FILE = "datos/preferencias.pkl"

def guardar_preferencias(usar_voz_entrada, usar_voz_salida):
    """Guarda las preferencias del usuario para futuras sesiones"""
    try:
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(PREFERENCIAS_FILE), exist_ok=True)

        # Guardar preferencias
        preferencias = {
            "usar_voz_entrada": usar_voz_entrada,
            "usar_voz_salida": usar_voz_salida
        }

        with open(PREFERENCIAS_FILE, "wb") as f:
            pickle.dump(preferencias, f)

        return True
    except Exception as e:
        print(f"Error al guardar preferencias: {e}")
        return False

def cargar_preferencias():
    """Carga las preferencias guardadas del usuario"""
    try:
        if os.path.exists(PREFERENCIAS_FILE):
            with open(PREFERENCIAS_FILE, "rb") as f:
                return pickle.load(f)
        return None
    except Exception as e:
        print(f"Error al cargar preferencias: {e}")
        return None

def reconocer_voz(modo_activacion="manual", tiempo_espera=5, tiempo_silencio=2):
    """
    Función para capturar audio y convertirlo a texto

    Parámetros:
    - modo_activacion:
        "manual" - Espera a que el usuario presione Enter para comenzar a escuchar
        "continuo" - Escucha continuamente hasta detectar silencio
        "palabra_clave" - Espera a escuchar una palabra clave para activarse
    - tiempo_espera: Tiempo máximo de espera para comenzar a hablar (segundos)
    - t iempo_silencio: Tiempo de silencio para considerar que terminó de hablar (segundos)
    """
    recognizer = sr.Recognizer()

    # Ajustar sensibilidad del reconocimiento
    recognizer.energy_threshold = 3000  # Ajustar según el ambiente
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = tiempo_silencio  # Tiempo de silencio para considerar fin de frase

    # Modo de activación manual (presionar Enter)
    if modo_activacion == "manual":
        input("\n🎤 Presiona Enter cuando estés listo para hablar...")
        print("🎙️ Escuchando... Habla ahora.")

        with sr.Microphone() as source:
            # Ajustar para ruido ambiental
            recognizer.adjust_for_ambient_noise(source, duration=1)

            try:
                # Capturar audio
                audio = recognizer.listen(source, timeout=tiempo_espera, phrase_time_limit=15)
                print("🔍 Procesando tu voz...")

                # Convertir audio a texto (usando Google Speech Recognition)
                texto = recognizer.recognize_google(audio, language="es-ES")
                print(f"🗣️ Has dicho: {texto}")

                # Verificar si el texto está vacío o es muy corto
                if not texto or len(texto) < 3:
                    print("❓ La consulta es demasiado corta. Por favor, intenta de nuevo.")
                    return None

                return texto

            except sr.WaitTimeoutError:
                print("⏱️ Tiempo de espera agotado. No se detectó ninguna voz.")
                return None
            except sr.UnknownValueError:
                print("❓ No se pudo entender lo que dijiste.")
                return None
            except sr.RequestError as e:
                print(f"🚫 Error en la solicitud al servicio de reconocimiento: {e}")
                return None

    # Modo continuo (escucha hasta detectar silencio)
    elif modo_activacion == "continuo":
        print("\n🎙️ Modo conversación activado. Habla cuando estés listo.")
        print("📢 Se detectará automáticamente cuando termines de hablar.")
        print("💡 Para salir del modo conversación, di 'salir' o quédate en silencio.")

        with sr.Microphone() as source:
            # Ajustar para ruido ambiental
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("🎤 Escuchando... Habla ahora.")

            try:
                # Capturar audio con detección automática de silencio
                audio = recognizer.listen(source, timeout=tiempo_espera, phrase_time_limit=20)
                print("🔍 Procesando tu voz...")

                # Convertir audio a texto
                texto = recognizer.recognize_google(audio, language="es-ES")
                print(f"🗣️ Has dicho: {texto}")

                # Verificar si el texto está vacío o es muy corto
                if not texto or len(texto) < 3:
                    print("❓ La consulta es demasiado corta. Por favor, intenta de nuevo.")
                    return None

                return texto

            except sr.WaitTimeoutError:
                print("⏱️ No se detectó ninguna voz. Saliendo del modo conversación.")
                return "salir del modo conversación"
            except sr.UnknownValueError:
                print("❓ No se pudo entender lo que dijiste.")
                return None
            except sr.RequestError as e:
                print(f"🚫 Error en la solicitud al servicio de reconocimiento: {e}")
                return None

    # Modo de palabra clave (para implementación futura)
    elif modo_activacion == "palabra_clave":
        print("\n🎤 Di 'Asistente' o 'Agenda' para activar el reconocimiento...")
        # Esta funcionalidad requeriría una implementación más compleja
        # que está fuera del alcance actual
        return reconocer_voz("manual")  # Por ahora, volvemos al modo manual

def hablar_texto(texto):
    """Función para convertir texto a voz"""
    try:
        # Inicializar el motor de voz
        engine = pyttsx3.init()

        # Configurar velocidad de habla
        engine.setProperty('rate', 150)

        # Configurar voz en español si está disponible
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'spanish' in voice.id.lower():
                engine.setProperty('voice', voice.id)
                break

        # Convertir texto a voz
        print("\n🔊 Reproduciendo respuesta por voz...")
        engine.say(texto)
        engine.runAndWait()
        return True
    except Exception as e:
        print(f"❌ Error al reproducir voz: {e}")
        return False

# Mostrar ejemplos de consultas
def mostrar_ejemplos_consultas():
    print("\n📋 EJEMPLOS DE CONSULTAS QUE PUEDES HACER:")
    print("------------------------------------------")
    ejemplos = [
        "¿Cuál es el teléfono de Juan Pérez?",
        "¿Qué dirección tiene Ana Ramírez?",
        "¿Cuál es el correo electrónico de Carlos?",
        "¿Cuántos años tiene Lucía?",
        "¿Cuántas personas hay en la agenda?",
        "¿Quién tiene más de 30 años?",
        "¿Quién es la persona más joven?",
        "Dame toda la información de Juan Pérez",
        "¿Hay alguien que viva en Colonia Centro?",
        "¿Quién es mayor, Juan o Ana?"
    ]
    for i, ejemplo in enumerate(ejemplos, 1):
        print(f"{i}. {ejemplo}")
    print("------------------------------------------")

# Clase para manejar el historial de conversación
class HistorialConversacion:
    def __init__(self, max_items=10):
        self.historial = []
        self.max_items = max_items

    def agregar(self, pregunta, respuesta):
        """Agrega una nueva entrada al historial"""
        self.historial.append({"pregunta": pregunta, "respuesta": respuesta})
        # Mantener solo los últimos max_items
        if len(self.historial) > self.max_items:
            self.historial.pop(0)

    def mostrar(self, num_items=None):
        """Muestra el historial de conversación"""
        if not self.historial:
            print("\n📝 No hay historial de conversación.")
            return

        items_a_mostrar = self.historial
        if num_items and num_items < len(self.historial):
            items_a_mostrar = self.historial[-num_items:]

        print("\n📜 HISTORIAL DE CONVERSACIÓN:")
        print("=" * 50)

        for i, item in enumerate(items_a_mostrar, 1):
            print(f"👤 Tú: {item['pregunta']}")
            print(f"🤖 Asistente: {item['respuesta']}")
            if i < len(items_a_mostrar):
                print("-" * 50)

        print("=" * 50)

    def obtener_ultima_respuesta(self):
        """Retorna la última respuesta del historial"""
        if self.historial:
            return self.historial[-1]["respuesta"]
        return None

    def limpiar(self):
        """Limpia todo el historial"""
        self.historial = []
        print("\n🧹 Historial de conversación limpiado.")

# Función para procesar una consulta
def procesar_consulta(pregunta, usar_voz_salida, historial=None):
    # Usar el enfoque centralizado de consultas
    resultado = process_query(pregunta, registros, esquema, mapeo_columnas, debug=True)
    texto_respuesta = resultado["response"]

    # Mostrar respuesta
    print("\n🧠 Respuesta del asistente:\n")
    print(texto_respuesta)

    # Agregar al historial si se proporcionó un objeto de historial
    if historial is not None:
        historial.agregar(pregunta, texto_respuesta)

    # Si el usuario eligió respuesta por voz, convertir texto a voz
    if usar_voz_salida:
        hablar_texto(texto_respuesta)

    return texto_respuesta

# Función principal que maneja la sesión
def main():
    # Inicializar la sesión
    print("=" * 50)
    print("ASISTENTE DE AGENDA")
    print("=" * 50)

    # Crear objeto para el historial de conversación
    historial = HistorialConversacion(max_items=20)

    # Intentar cargar preferencias guardadas
    preferencias = cargar_preferencias()

    # Valores por defecto
    usar_voz_entrada = False
    usar_voz_salida = False

    if preferencias:
        print("\n🔄 Se encontraron preferencias guardadas:")
        print(f"- Entrada por {'voz' if preferencias['usar_voz_entrada'] else 'texto'}")
        print(f"- Salida por {'voz' if preferencias['usar_voz_salida'] else 'texto'}")
        usar_guardadas = input("¿Deseas usar estas preferencias? (s/n): ").lower() == 's'

        if usar_guardadas:
            usar_voz_entrada = preferencias['usar_voz_entrada']
            usar_voz_salida = preferencias['usar_voz_salida']

    # Si es necesario configurar el modo
    if not preferencias or not usar_guardadas:
        print("\n⚙️ Configuración del modo de interacción:")
        print("1. Todo en texto (escribir consultas y recibir respuestas en texto)")
        print("2. Todo por voz (consultas por voz y respuestas por voz)")
        print("3. Consultas por voz, respuestas en texto")
        print("4. Consultas en texto, respuestas por voz")
        print("5. Configuración personalizada")

        opcion_modo = input("Selecciona un modo (1-5): ")

        # Configurar según la opción elegida
        if opcion_modo == "1":
            # Todo en texto
            usar_voz_entrada = False
            usar_voz_salida = False
        elif opcion_modo == "2":
            # Todo por voz
            usar_voz_entrada = True
            usar_voz_salida = True
        elif opcion_modo == "3":
            # Consultas por voz, respuestas en texto
            usar_voz_entrada = True
            usar_voz_salida = False
        elif opcion_modo == "4":
            # Consultas en texto, respuestas por voz
            usar_voz_entrada = False
            usar_voz_salida = True
        else:
            # Configuración personalizada
            print("\n¿Cómo prefieres hacer tus consultas?")
            print("1. Escribir consultas")
            print("2. Consultas por voz")
            opcion_entrada = input("Selecciona una opción (1/2): ")
            usar_voz_entrada = opcion_entrada == "2"

            print("\n¿Cómo prefieres recibir las respuestas?")
            print("1. Texto en pantalla")
            print("2. Respuesta por voz")
            opcion_salida = input("Selecciona una opción (1/2): ")
            usar_voz_salida = opcion_salida == "2"

        # Preguntar si desea guardar las preferencias
        guardar = input("\n¿Deseas guardar estas preferencias para futuras sesiones? (s/n): ").lower() == 's'
        if guardar:
            if guardar_preferencias(usar_voz_entrada, usar_voz_salida):
                print("✅ Preferencias guardadas correctamente.")
            else:
                print("❌ No se pudieron guardar las preferencias.")

    # Mostrar ejemplos de consultas
    mostrar_ejemplos_consultas()

    # Mostrar comandos especiales
    print("\n⌨️ COMANDOS ESPECIALES:")
    print("------------------------------------------")
    print("- Escribe 'salir' para terminar el programa")
    print("- Escribe 'modo' para cambiar el modo de interacción")
    print("- Escribe 'ejemplos' para ver ejemplos de consultas")
    print("- Escribe 'guardar' para guardar las preferencias actuales")
    print("- Escribe 'historial' para ver el historial de conversación")
    print("- Escribe 'limpiar' para limpiar el historial")
    print("- Escribe 'conversar' para activar el modo conversación continua")
    print("------------------------------------------")

    # Bucle principal de la sesión
    sesion_activa = True
    while sesion_activa:
        print("\n" + "=" * 50)
        print(f"📝 Nueva consulta - Modo: {'Voz' if usar_voz_entrada else 'Texto'} (entrada) | {'Voz' if usar_voz_salida else 'Texto'} (salida)")
        print("=" * 50)

        # Obtener la pregunta según la opción elegida
        if usar_voz_entrada:
            print("\n🎙️ Puedes hacer cualquiera de las consultas de ejemplo o formular tu propia pregunta.")

            # Opciones para el reconocimiento de voz
            print("\n🔄 Opciones de reconocimiento de voz:")
            print("1. Presionar Enter para hablar (recomendado)")
            print("2. Cambiar a entrada de texto para esta consulta")
            opcion_reconocimiento = input("Selecciona una opción (1/2): ")

            if opcion_reconocimiento == "2":
                # Cambiar temporalmente a entrada de texto
                pregunta = input("\nHaz tu consulta: ")
            else:
                # Intentar reconocimiento de voz con hasta 2 reintentos
                max_intentos = 3
                for intento in range(1, max_intentos + 1):
                    pregunta = reconocer_voz("manual")  # Modo de activación manual

                    if pregunta is not None:
                        break  # Si se reconoció correctamente, salir del bucle

                    if intento < max_intentos:
                        print(f"\n🔄 Intento {intento} de {max_intentos} fallido.")
                        continuar_voz = input("¿Quieres intentar de nuevo con voz? (s/n): ").lower() == 's'
                        if not continuar_voz:
                            print("\n⌨️ Cambiando a entrada de texto.")
                            pregunta = input("Haz tu consulta: ")
                            break

                # Si después de todos los intentos no se reconoció nada, usar texto
                if pregunta is None:
                    print("\n⌨️ No se pudo reconocer tu voz. Por favor, escribe tu consulta:")
                    pregunta = input("Haz tu consulta: ")
        else:
            pregunta = input("\nHaz tu consulta: ")

        # Verificar comandos especiales
        comando = pregunta.lower().strip()

        # Comando para salir
        if comando in ["salir", "exit", "quit", "terminar", "finalizar"]:
            print("\n👋 Gracias por usar el asistente de agenda. ¡Hasta pronto!")
            sesion_activa = False
            break

        # Comando para cambiar el modo
        elif comando == "modo":
            print("\n⚙️ Cambiar modo de interacción:")
            print("1. Todo en texto (escribir consultas y recibir respuestas en texto)")
            print("2. Todo por voz (consultas por voz y respuestas por voz)")
            print("3. Consultas por voz, respuestas en texto")
            print("4. Consultas en texto, respuestas por voz")

            nuevo_modo = input("Selecciona un modo (1-4): ")

            if nuevo_modo == "1":
                usar_voz_entrada = False
                usar_voz_salida = False
                print("\n✅ Modo cambiado a: Todo en texto")
            elif nuevo_modo == "2":
                usar_voz_entrada = True
                usar_voz_salida = True
                print("\n✅ Modo cambiado a: Todo por voz")
            elif nuevo_modo == "3":
                usar_voz_entrada = True
                usar_voz_salida = False
                print("\n✅ Modo cambiado a: Consultas por voz, respuestas en texto")
            elif nuevo_modo == "4":
                usar_voz_entrada = False
                usar_voz_salida = True
                print("\n✅ Modo cambiado a: Consultas en texto, respuestas por voz")
            else:
                print("\n❌ Opción no válida. Se mantiene el modo actual.")

            continue

        # Comando para mostrar ejemplos
        elif comando == "ejemplos":
            mostrar_ejemplos_consultas()
            continue

        # Comando para guardar preferencias
        elif comando == "guardar":
            if guardar_preferencias(usar_voz_entrada, usar_voz_salida):
                print("✅ Preferencias guardadas correctamente.")
            else:
                print("❌ No se pudieron guardar las preferencias.")
            continue

        # Comando para mostrar historial
        elif comando == "historial":
            historial.mostrar()
            continue

        # Comando para limpiar historial
        elif comando == "limpiar":
            historial.limpiar()
            continue



        # Comando para activar modo conversación
        elif comando == "conversar":
            print("\n🎙️ Activando modo conversación continua...")
            print("💡 En este modo, el sistema escuchará automáticamente después de cada respuesta.")
            print("💡 Para salir del modo conversación, di 'salir' o quédate en silencio.")

            # Bucle de conversación continua
            modo_conversacion_activo = True
            while modo_conversacion_activo and sesion_activa:
                # Obtener pregunta por voz en modo continuo
                pregunta_voz = reconocer_voz("continuo", tiempo_espera=7, tiempo_silencio=2)

                # Verificar si se debe salir del modo conversación
                if pregunta_voz is None or pregunta_voz.lower() in ["salir", "exit", "terminar", "salir del modo conversación"]:
                    print("\n🔄 Saliendo del modo conversación continua.")
                    modo_conversacion_activo = False
                    continue

                # Procesar la consulta y guardar en historial
                procesar_consulta(pregunta_voz, usar_voz_salida, historial)

            continue

        # Si no es un comando especial, procesar como consulta normal
        else:
            # Procesar la consulta y guardar en historial
            procesar_consulta(pregunta, usar_voz_salida, historial)

# Ejecutar el programa
if __name__ == "__main__":
    main()
