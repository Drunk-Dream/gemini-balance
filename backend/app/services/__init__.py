from app.core.config import settings
from app.services.key_managers import get_key_manager

key_manager = get_key_manager(settings)
