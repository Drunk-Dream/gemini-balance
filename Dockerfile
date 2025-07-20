# Stage 1: Frontend Builder
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ . .
RUN npm run build

# Stage 2: Backend Builder
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS backend-builder

# Set environment variables, avoid .pyc files, and unbuffered output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app/backend

# Copy pyproject.toml and uv.lock to the working directory
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies using uv
RUN uv sync

# Copy the rest of the backend application code
COPY backend/ . .

# Copy frontend build artifacts from the frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose the port the app runs on
EXPOSE 8090

# Run the application
CMD ["uv", "run", "-m", "main"]
