FROM python:3.8-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY ./requirements.txt .
RUN python -m pip install -r requirements.txt

RUN python -m pip install -i https://test.pypi.org/simple/ IoTomatoes-SupportPackage --no-deps

WORKDIR /app

COPY ./Truck1/ /app/
COPY ./FakeTruck.py /app/

CMD ["python","FakeTruck.py"]
