# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set environment variables, avoid .pyc files, and unbuffered output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install uv
RUN pip install uv

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
