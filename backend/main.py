import os

import uvicorn
from dotenv import load_dotenv


def main():
    load_dotenv()
    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", 8090))
    # Read APP_ENV, default to 'production' if not set
    app_env = os.getenv("APP_ENV", "production")
    # Enable reload only in 'development' environment
    should_reload = app_env.lower() == "development"
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=should_reload)


if __name__ == "__main__":
    main()
