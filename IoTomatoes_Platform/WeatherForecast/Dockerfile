FROM python:3.8-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY ./WeatherForecast/requirements.txt .
RUN python -m pip install -r requirements.txt

RUN python -m pip install -i https://test.pypi.org/simple/ IoTomatoes-SupportPackage --no-deps

WORKDIR /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 8082 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

COPY ./WeatherForecast/ /app/

CMD ["python","/app/WeatherForecast.py"]
