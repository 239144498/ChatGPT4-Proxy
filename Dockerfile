FROM python:3.9-slim
LABEL maintainer="Naihe <239144498@qq.com>"

RUN apt-get update -y && \
    pip install --no-cache-dir --upgrade -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
