FROM python:3.12-slim

WORKDIR /app/apps/api

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

COPY apps/api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api .

EXPOSE 3001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"]