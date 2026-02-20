# Rate Limiting configuration pour KALGA API
# Utilise slowapi pour protéger contre les abus

from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter global - utilise l'IP du client comme clé
limiter = Limiter(key_func=get_remote_address)
