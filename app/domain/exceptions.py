class DomainError(Exception):
    """Error de negocio. El mensaje va en español y se muestra al cliente."""


class NotFoundError(DomainError):
    """El recurso no existe o no pertenece al estudiante actual."""


class ConflictError(DomainError):
    """La operación choca con el estado actual (correo duplicado, examen ya enviado)."""


class InvalidDataError(DomainError):
    """Datos que pasan la validación de formato pero violan una regla de negocio."""


class AuthenticationError(DomainError):
    """Credenciales o token inválidos."""
