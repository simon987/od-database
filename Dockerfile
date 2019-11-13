FROM python:3.7

WORKDIR /app

ADD requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "app.py"]

COPY . /app

