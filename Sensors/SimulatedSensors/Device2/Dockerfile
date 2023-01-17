FROM python:3.8-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY ./Sensors/SimulatedSensors/requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN adduser -u 8080 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

COPY ./Sensors/SimulatedSensors/Device1/ /app/
COPY ./Sensors/SimulatedSensors/AmbientSimulator.py /app/
COPY ./Sensors/SimulatedSensors/FakeSensor.py /app/
COPY ./SupportClasses/ /app/

CMD ["python","/app/FakeSensor.py"]
