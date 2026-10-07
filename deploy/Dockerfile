FROM python:3.13.12-slim@sha256:f1927c75e81efd1e091dbd64b6c0ecaa5630b38635a3d1c04034ac636e1f94c8 AS hermes-build
ARG HERMES_REVISION=dd0e4ab81abccf7df5b11c6c16853d5e5de9db69
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN git init /opt/hermes && cd /opt/hermes && git remote add origin https://github.com/NousResearch/hermes-agent.git && git fetch --depth=1 origin ${HERMES_REVISION} && git checkout --detach FETCH_HEAD && test "$(git rev-parse HEAD)" = "${HERMES_REVISION}"
RUN pip install --no-cache-dir uv==0.10.12 && cd /opt/hermes && uv sync --frozen --no-dev --python /usr/local/bin/python
RUN printf '%s' "${HERMES_REVISION}" > /opt/hermes/REVISION

FROM python:3.13.12-slim@sha256:f1927c75e81efd1e091dbd64b6c0ecaa5630b38635a3d1c04034ac636e1f94c8 AS app
RUN groupadd -g 11001 habnews && useradd -u 11001 -g 11001 -m -d /home/habnews habnews
WORKDIR /app
COPY pyproject.toml .
COPY habnews habnews
COPY schemas schemas
COPY sources.yaml .
COPY deploy/verify-container.py /app/verify-container.py
COPY deploy/record-readiness.py /app/record-readiness.py
COPY deploy/send-labelled-test.py /app/send-labelled-test.py
RUN pip install --no-cache-dir . && rm -rf /root/.cache
USER 11001:11001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "habnews.cli"]

FROM app AS runner
COPY --from=hermes-build /opt/hermes /opt/hermes
COPY deploy/hermes-config.yaml /app/hermes-config.yaml
COPY deploy/runner_entry.py /app/runner_entry.py
ENV HERMES_HOME=/auth/habnews CODEX_HOME=/home/habnews/empty-codex PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["/opt/hermes/.venv/bin/python", "/app/runner_entry.py"]
