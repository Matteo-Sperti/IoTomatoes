FROM python:3.8-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY ./requirements.txt .
RUN python3 -m pip install -r requirements.txt

RUN python3 -m pip install -i https://test.pypi.org/simple/ IoTomatoes-SupportPackage==0.0.10 --no-deps

WORKDIR /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN adduser -u 8080 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

COPY ./Device1/ /app/
COPY ./FakeDevice.py /app/

CMD ["python3","FakeDevice.py"]
