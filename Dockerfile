FROM python:2
ADD yardly.py /
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -yq python-usb
COPY ./rfcat/rflib /usr/local/lib/python2.7/site-packages/rflib
COPY ./rfcat/vstruct /usr/local/lib/python2.7/site-packages/vstruct
CMD [ "python2", "./yardly.py" ]

