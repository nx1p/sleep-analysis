FROM python:3.11.9-alpine3.20

# Install poetry
RUN pip install poetry==1.5.1

RUN apk add --update --no-cache p7zip


# Set environment variables
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    DATA_DIR=/app

WORKDIR /app

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* ./

# Install project (and dependencies)
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# Copy only the necessary files
COPY http_server.py ./
COPY import_to_db.py ./

# Create data directory
#RUN mkdir -p /app/data

# Run the application
CMD ["poetry", "run", "python", "http_server.py"]