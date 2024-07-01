FROM python:slim-bookworm

WORKDIR /python-docker

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt && apt-get update && apt-get install -y ghostscript libdmtx-dev fonts-dejavu-core

COPY . .

CMD [ "python3", "-m" , "tg_adapter"]