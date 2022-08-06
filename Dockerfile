FROM python:3.9
WORKDIR /indexer
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8080
VOLUME /indexer/data
CMD ["python", "-u", "indexer"]