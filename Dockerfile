FROM python:3.6.8
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y netcat && \
    apt-get install -y build-essential libffi-dev python-dev

# Set the working directory to /app
WORKDIR /app

# Install any needed packages specified in requirements.txt
ADD requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the current directory contents into the container at /app
ADD . /app/

EXPOSE 1700 1700

ENTRYPOINT ["/app/run_server.sh"]