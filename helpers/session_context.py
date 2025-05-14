"""
Módulo para manejar el contexto de la sesión en el asistente de agenda.
Mantiene un historial de interacciones y proporciona contexto para las consultas.
"""

class SessionContext:
    """
    Clase para manejar el contexto de la sesión.
    Mantiene un historial de interacciones y proporciona contexto para las consultas.
    """
    
    def __init__(self, max_history=5):
        """
        Inicializa un nuevo contexto de sesión.
        
        Args:
            max_history (int): Número máximo de interacciones a mantener en el historial
        """
        self.interactions = []
        self.max_history = max_history
        self.current_session_id = 1
        self.last_mentioned_person = None
        self.last_mentioned_attribute = None
    
    def add_interaction(self, query, parameters, response):
        """
        Añade una nueva interacción al historial.
        
        Args:
            query (str): Consulta del usuario
            parameters (dict): Parámetros extraídos de la consulta
            response (str): Respuesta generada
        """
        # Extraer información relevante de los parámetros
        person = parameters.get("persona")
        attribute = parameters.get("atributo")
        
        # Actualizar última persona y atributo mencionados
        if person:
            self.last_mentioned_person = person
        if attribute:
            self.last_mentioned_attribute = attribute
        
        # Crear registro de interacción
        interaction = {
            "session_id": self.current_session_id,
            "query": query,
            "parameters": parameters,
            "response": response,
            "person": person,
            "attribute": attribute
        }
        
        # Añadir al historial
        self.interactions.append(interaction)
        
        # Mantener solo las últimas max_history interacciones
        if len(self.interactions) > self.max_history:
            self.interactions.pop(0)
    
    def get_context_for_prompt(self):
        """
        Obtiene información de contexto para incluir en el prompt.
        
        Returns:
            dict: Información de contexto para el prompt
        """
        context = {
            "session_id": self.current_session_id,
            "interaction_count": len(self.interactions),
            "last_mentioned_person": self.last_mentioned_person,
            "last_mentioned_attribute": self.last_mentioned_attribute,
            "recent_interactions": []
        }
        
        # Añadir las últimas 3 interacciones (o menos si no hay suficientes)
        for interaction in self.interactions[-3:]:
            context["recent_interactions"].append({
                "query": interaction["query"],
                "response": interaction["response"]
            })
        
        return context
    
    def is_follow_up_query(self, query):
        """
        Determina si una consulta es de seguimiento basada en el contexto.
        
        Args:
            query (str): Consulta a analizar
            
        Returns:
            bool: True si es una consulta de seguimiento, False en caso contrario
        """
        # Si no hay interacciones previas, no puede ser seguimiento
        if not self.interactions:
            return False
        
        query_lower = query.lower()
        
        # Verificar si la consulta contiene pronombres o referencias implícitas
        pronouns = ["él", "ella", "su", "sus", "le", "lo", "la"]
        references = ["también", "tampoco", "y", "además", "otra", "otro", "ese", "esa", "este", "esta"]
        
        # Verificar si contiene pronombres o referencias
        if any(word in query_lower for word in pronouns + references):
            return True
        
        # Verificar si es una consulta muy corta (posible seguimiento)
        if len(query.split()) <= 4:
            return True
        
        # Verificar si menciona la misma persona que la consulta anterior
        if self.last_mentioned_person and self.last_mentioned_person.lower() in query_lower:
            # Si solo menciona la persona pero no especifica atributo, podría ser seguimiento
            if not any(attr in query_lower for attr in ["teléfono", "telefono", "dirección", "direccion", "correo", "email", "edad", "años"]):
                return True
        
        return False
    
    def reset_session(self):
        """
        Reinicia la sesión actual.
        """
        self.interactions = []
        self.current_session_id += 1
        self.last_mentioned_person = None
        self.last_mentioned_attribute = None
