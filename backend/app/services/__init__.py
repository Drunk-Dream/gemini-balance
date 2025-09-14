from backend.app.core.config import settings
from backend.app.services.key_managers import get_key_manager

key_manager = get_key_manager(settings)
