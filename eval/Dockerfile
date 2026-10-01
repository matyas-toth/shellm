FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
RUN useradd --uid 1000 --create-home shellm \
    && command -v bash && command -v find && command -v grep && command -v wc
COPY worker.py /opt/shellbench-worker.py
USER 1000:1000
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python", "-I", "/opt/shellbench-worker.py"]
