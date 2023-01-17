FROM python:3.8-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY ./ResourceCatalog/requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN adduser -u 8081 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

COPY ./ResourceCatalog/ /app/
COPY ./SupportClasses/ /app/

RUN pip install -r /app/requirements.txt
RUN cd /app/
CMD ["python","/app/ResourceCatalog.py"]
