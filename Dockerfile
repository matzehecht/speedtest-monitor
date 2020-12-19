FROM python:3.8-slim-buster

WORKDIR /speedie

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get -q -y autoremove
RUN apt-get -q -y clean
RUN rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY . ./

CMD ["python3", "main.py"]