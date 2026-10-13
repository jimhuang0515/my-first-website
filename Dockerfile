FROM node:24-bookworm-slim AS frontend-build
WORKDIR /build/frontend
ENV NEXT_TELEMETRY_DISABLED=1
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=secret,id=build_ca,mode=0444 \
    if [ -s /run/secrets/build_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; fi; \
    npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
RUN --mount=type=secret,id=build_ca,mode=0444 \
    set -eu; set --; \
    if [ -s /run/secrets/build_ca ]; then set -- -o Acquire::https::CaInfo=/run/secrets/build_ca; fi; \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get "$@" -o APT::Update::Error-Mode=any update \
    && apt-get "$@" install -y --no-install-recommends libstdc++6 libatomic1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements.lock ./backend/requirements.lock
RUN --mount=type=secret,id=build_ca,mode=0444 \
    if [ -s /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    pip install --no-cache-dir --disable-pip-version-check -r backend/requirements.lock
COPY backend/app ./backend/app
COPY --from=frontend-build /build/frontend/.next/standalone ./frontend
COPY --from=frontend-build /build/frontend/.next/static ./frontend/.next/static
COPY scripts/start-production.sh ./scripts/start-production.sh
RUN useradd --create-home --uid 10001 stocklab && chown -R stocklab:stocklab /app
USER stocklab
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PYTHONUNBUFFERED=1
EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c 'import os,urllib.request; urllib.request.urlopen("http://127.0.0.1:"+os.getenv("PORT","10000")+"/api/v1/health",timeout=3)'
CMD ["bash", "/app/scripts/start-production.sh"]
