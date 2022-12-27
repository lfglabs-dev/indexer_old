FROM python:3.9
WORKDIR /indexer
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED "1"
CMD ["python", "-u", "indexer"]