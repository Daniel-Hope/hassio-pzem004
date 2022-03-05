
FROM python:3.7-buster

ENV LANG C.UTF-8

# Install requirements for add-on
RUN pip3 install --no-cache-dir pyserial

COPY run.py /
RUN chmod a+x /run.py

cmd [ "python", "./run.py" ]
