ARG BUILD_FROM
FROM ${BUILD_FROM}

# Addon metadata
LABEL io.hass.name="EchoMind - AI Memory Layer"
LABEL io.hass.description="Personal Memory Layer for AI Applications with Home Assistant Integration. All memory remains local."
LABEL io.hass.version="1.0.0"
LABEL io.hass.slug="echomind"
LABEL io.hass.arch="$BUILD_ARCH"
LABEL maintainer="mercuryin <[tu_email_o_contacto_aqui]>" 
LABEL io.hass.url="https://github.com/mercuryin/EchoMind_ha"

# Actualizar repositorios y limpiar caché
RUN apk update && apk upgrade && rm -rf /var/cache/apk/*

# Instalar dependencias básicas y de compilación
RUN apk add --no-cache \
    bash \
    curl \
    git \
    jq \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    py3-cryptography \
    py3-requests \
    py3-urllib3 \
    py3-certifi \
    py3-chardet \
    py3-idna \
    py3-six \
    build-base \
    python3-dev \
    gcc \
    musl-dev \
    linux-headers \
    rust \
    cargo \
    openssl-dev \
    libffi-dev \
    ca-certificates && \
    update-ca-certificates

# Crear directorio de trabajo
WORKDIR /app

# Verificar versión de Python
RUN python3 --version && pip3 --version

# Clonar el repositorio original de your-memory
RUN git clone https://github.com/jonathan-politzki/your-memory.git .

# Instalar dependencias de Python en orden específico
RUN pip3 install --no-cache-dir pytz==2024.1 && \
    pip3 install --no-cache-dir pydantic==2.7.3 && \
    pip3 install --no-cache-dir sqlalchemy==2.0.31 && \
    pip3 install --no-cache-dir neo4j==5.23.1 && \
    pip3 install --no-cache-dir qdrant-client==1.9.1 && \
    pip3 install --no-cache-dir openai==1.33.0 && \
    pip3 install --no-cache-dir posthog==3.5.0 && \
    pip3 install --no-cache-dir langchain-neo4j==0.4.0 && \
    pip3 install --no-cache-dir rank-bm25==0.2.2

# Limpiar herramientas de compilación
RUN apk del build-base python3-dev gcc musl-dev linux-headers rust cargo openssl-dev libffi-dev

# Copiar archivos de configuración y scripts específicos del addon
COPY rootfs/ / 

# Hacer ejecutables los scripts importantes
RUN chmod +x /run.sh && \
    chmod +x /usr/bin/echomind-ha-setup

# Exponer los puertos que la aplicación utilizará
EXPOSE 8765 3000

# Comando por defecto para iniciar el addon
CMD [ "/run.sh" ]
