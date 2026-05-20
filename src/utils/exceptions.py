# src/utils/exceptions.py

class APIException(Exception):
    """
    Excepción personalizada para estandarizar las respuestas de error en la API.
    """
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message

