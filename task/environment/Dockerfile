FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN pip install --no-cache-dir \
      numpy==2.3.5 \
      pytest==8.4.1 \
      pytest-json-ctrf==0.3.5

WORKDIR /app

RUN mkdir -p /app/output /app/data /app/fit /app/docs /app/bin /app/lib

COPY data/ /app/data/
COPY fit/ /app/fit/
COPY docs/ /app/docs/
COPY lib/ /app/lib/
COPY sae_ref/sae_ref.py /app/bin/sae_ref
COPY sae_ref/fit_hashes.json /app/bin/fit_hashes.json

RUN chmod 0755 /app/bin/sae_ref
