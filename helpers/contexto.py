"""
Módulo para manejar el contexto de la conversación en el asistente de agenda.
"""

class ContextoConversacion:
    """
    Clase para mantener el contexto de la conversación durante una sesión.
    Permite que el asistente recuerde información previa y mantenga una
    conversación más coherente y natural.
    """
    
    def __init__(self, max_historial=5):
        """
        Inicializa un nuevo contexto de conversación.
        
        Args:
            max_historial (int): Número máximo de intercambios a recordar
        """
        self.ultima_persona_mencionada = None
        self.ultimo_atributo_consultado = None
        self.ultima_pregunta = None
        self.ultima_respuesta = None
        self.historial = []
        self.max_historial = max_historial
        self.saludos_realizados = 0
        self.consultas_realizadas = 0
    
    def actualizar(self, pregunta, respuesta):
        """
        Actualiza el contexto con una nueva pregunta y respuesta.
        
        Args:
            pregunta (str): Pregunta del usuario
            respuesta (str): Respuesta del asistente
        """
        # Guardar pregunta y respuesta anteriores en el historial
        if self.ultima_pregunta and self.ultima_respuesta:
            self.historial.append({
                "pregunta": self.ultima_pregunta,
                "respuesta": self.ultima_respuesta
            })
            
            # Mantener solo los últimos max_historial intercambios
            if len(self.historial) > self.max_historial:
                self.historial.pop(0)
        
        # Actualizar última pregunta y respuesta
        self.ultima_pregunta = pregunta
        self.ultima_respuesta = respuesta
        self.consultas_realizadas += 1
        
        # Detectar persona mencionada
        personas = ["Juan", "Ana", "Carlos", "Lucía", "Lucia"]
        pregunta_lower = pregunta.lower()
        
        for persona in personas:
            if persona.lower() in pregunta_lower:
                self.ultima_persona_mencionada = persona
                break
        
        # Detectar atributo consultado
        atributos = {
            "telefono": ["teléfono", "telefono", "número", "numero", "llamar", "celular"],
            "direccion": ["dirección", "direccion", "vive", "casa", "domicilio", "ubicación", "ubicacion"],
            "correo": ["correo", "email", "mail", "e-mail", "electrónico", "electronico"],
            "edad": ["edad", "años", "cumplió", "cumple", "nació", "nacio"],
            "genero": ["género", "genero", "sexo", "hombre", "mujer"]
        }
        
        for atributo, palabras_clave in atributos.items():
            if any(palabra in pregunta_lower for palabra in palabras_clave):
                self.ultimo_atributo_consultado = atributo
                break
    
    def obtener_contexto_para_prompt(self):
        """
        Genera un texto con el contexto relevante para incluir en el prompt.
        
        Returns:
            str: Texto con el contexto para el prompt
        """
        contexto = []
        
        # Incluir información sobre la última persona mencionada
        if self.ultima_persona_mencionada:
            contexto.append(f"- La última persona mencionada fue: {self.ultima_persona_mencionada}")
        
        # Incluir información sobre el último atributo consultado
        if self.ultimo_atributo_consultado:
            contexto.append(f"- El último atributo consultado fue: {self.ultimo_atributo_consultado}")
        
        # Incluir las últimas interacciones (máximo 2)
        if self.historial:
            contexto.append("- Últimas interacciones:")
            for i, interaccion in enumerate(self.historial[-2:]):
                contexto.append(f"  Usuario: {interaccion['pregunta']}")
                contexto.append(f"  Asistente: {interaccion['respuesta']}")
        
        # Incluir la última pregunta
        if self.ultima_pregunta:
            contexto.append(f"- Pregunta actual: {self.ultima_pregunta}")
        
        # Incluir información sobre el número de consultas
        contexto.append(f"- Esta es la consulta número {self.consultas_realizadas + 1} en esta sesión")
        
        # Si es la primera interacción, indicarlo
        if self.consultas_realizadas == 0:
            contexto.append("- Esta es la primera interacción con el usuario")
        
        return "\n".join(contexto)
    
    def es_pregunta_seguimiento(self, pregunta):
        """
        Determina si una pregunta es de seguimiento basada en el contexto.
        
        Args:
            pregunta (str): Pregunta a analizar
            
        Returns:
            bool: True si es una pregunta de seguimiento, False en caso contrario
        """
        pregunta_lower = pregunta.lower()
        
        # Verificar si la pregunta contiene pronombres o referencias implícitas
        referencias = ["él", "ella", "su", "sus", "le", "lo", "la", "también", "tampoco", 
                      "y", "además", "otra cosa", "por cierto", "y qué hay de"]
        
        if any(ref in pregunta_lower for ref in referencias):
            return True
        
        # Verificar si la pregunta es muy corta (posible seguimiento)
        if len(pregunta.split()) <= 5 and self.ultima_pregunta:
            return True
        
        # Verificar si menciona la misma persona que la pregunta anterior
        if self.ultima_persona_mencionada and self.ultima_persona_mencionada.lower() in pregunta_lower:
            return True
        
        return False
