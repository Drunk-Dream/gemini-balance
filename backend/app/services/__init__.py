from app.core.config import settings
from app.services.auth_key_manager import get_auth_db_manager
from app.services.key_managers import get_key_manager

key_manager = get_key_manager(settings)
auth_key_manager = get_auth_db_manager(settings)
