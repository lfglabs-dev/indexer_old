FROM python:3.9
WORKDIR /indexer
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8082
VOLUME /indexer/data
ENV PYTHONUNBUFFERED "1"
CMD ["python", "-u", "indexer"]