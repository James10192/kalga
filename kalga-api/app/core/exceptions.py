"""
Exceptions personnalisées pour KALGA
Permet une gestion d'erreurs cohérente et informative
"""
from typing import Optional, Any


class KalgaException(Exception):
    """Exception de base pour toutes les erreurs KALGA"""

    def __init__(
        self,
        message: str,
        code: str = "KALGA_ERROR",
        details: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details
        }


# === Exceptions Métier ===

class MerchantNotFoundError(KalgaException):
    """Marchand non trouvé"""

    def __init__(self, identifier: str):
        super().__init__(
            message=f"Marchand non trouvé: {identifier}",
            code="MERCHANT_NOT_FOUND",
            details={"identifier": identifier}
        )


class ProductNotFoundError(KalgaException):
    """Produit non trouvé"""

    def __init__(self, code: str):
        super().__init__(
            message=f"Produit non trouvé: {code}",
            code="PRODUCT_NOT_FOUND",
            details={"product_code": code}
        )


class ConversationNotFoundError(KalgaException):
    """Conversation non trouvée"""

    def __init__(self, conversation_id: int):
        super().__init__(
            message=f"Conversation non trouvée: {conversation_id}",
            code="CONVERSATION_NOT_FOUND",
            details={"conversation_id": conversation_id}
        )


class SessionExpiredError(KalgaException):
    """Session de création expirée"""

    def __init__(self, merchant_phone: str):
        super().__init__(
            message=f"Session expirée pour {merchant_phone}",
            code="SESSION_EXPIRED",
            details={"merchant_phone": merchant_phone}
        )


class ValidationError(KalgaException):
    """Erreur de validation des données"""

    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation échouée pour '{field}': {message}",
            code="VALIDATION_ERROR",
            details={"field": field, "reason": message}
        )


# === Exceptions Techniques ===

class DatabaseError(KalgaException):
    """Erreur de base de données"""

    def __init__(self, operation: str, details: str = ""):
        super().__init__(
            message=f"Erreur DB lors de '{operation}': {details}",
            code="DATABASE_ERROR",
            details={"operation": operation}
        )


class ExternalServiceError(KalgaException):
    """Erreur de service externe (DeepSeek, WhatsApp)"""

    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"Erreur service externe '{service}': {message}",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service}
        )


class WhatsAppBridgeError(ExternalServiceError):
    """Erreur spécifique au bridge WhatsApp"""

    def __init__(self, message: str):
        super().__init__(service="WhatsApp Bridge", message=message)


class DeepSeekError(ExternalServiceError):
    """Erreur spécifique à DeepSeek"""

    def __init__(self, message: str):
        super().__init__(service="DeepSeek API", message=message)
