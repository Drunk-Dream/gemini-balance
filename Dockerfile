# Use an official uv runtime as a parent image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set environment variables, avoid .pyc files, and unbuffered output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy pyproject.toml and uv.lock to the working directory
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8090

# Run the application
CMD ["uv", "run", "-m", "main"]
