FROM python:3.8-slim as base

# Install Python dependencies in an intermediate image
# as some requires a compiler (psycopg2)
FROM base as builder

# Install dependencies required to compile some Python packages
# Taken from https://github.com/docker-library/python/blob/master/3.8/buster/slim/Dockerfile
# For psycopg2: libpq-dev
RUN apt-get update \
  && apt-get install -yq --no-install-recommends \
  dpkg-dev \
  gcc \
  libbluetooth-dev \
  libbz2-dev \
  libc6-dev \
  libexpat1-dev \
  libffi-dev \
  libgdbm-dev \
  liblzma-dev \
  libncursesw5-dev \
  libpq-dev \
  libreadline-dev \
  libsqlite3-dev \
  libssl-dev \
  make \
  tk-dev \
  uuid-dev \
  wget \
  xz-utils \
  zlib1g-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
RUN python3 -m venv /venv \
  && . /venv/bin/activate \
  && pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r /requirements.txt \
  && pip install --no-cache-dir psycopg2

FROM base

RUN groupadd -r -g 1000 csi \
  && useradd --no-log-init -r -g csi -u 1000 csi

COPY --chown=csi:csi --from=builder  /venv /venv

# Install libraries for psycopg2
RUN apt-get update \
  && apt-get install -yq --no-install-recommends \
  libpq5 \
  git \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY --chown=csi:csi . /app/
WORKDIR /app

ENV PATH /venv/bin:$PATH

# Install the app so it can be found by alembic
RUN pip install --no-cache-dir .

USER 1000

# Running uvicorn is for testing
# For production, run using Gunicorn using the uvicorn worker class
# Use one or two workers per-CPU core
# For example:
# gunicorn -w 4 -k uvicorn.workers.UvicornWorker --log-level warning main:app
CMD ["uvicorn", "--proxy-headers", "--host", "0.0.0.0", "--port", "8000", "app.main:app"]
