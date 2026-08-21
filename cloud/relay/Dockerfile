FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /srv
COPY cloud/relay/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY cloud/relay ./cloud/relay

CMD ["python", "-m", "uvicorn", "cloud.relay.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
