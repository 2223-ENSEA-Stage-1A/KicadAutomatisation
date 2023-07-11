# Start with a base image (choose an appropriate Linux distribution)
FROM ubuntu:20.04

# Set the working directory
WORKDIR /app

# Copy the project files
COPY /myproject .

# Update and install necessary dependencies for Kicad
RUN apt update
RUN apt-get install -y software-properties-common
RUN apt update
RUN add-apt-repository --yes ppa:kicad/kicad-7.0-releases
RUN apt update
RUN apt install --no-install-recommends -y kicad

# Install Python
RUN apt-get install -y python3 python3-pip

# Install the latest version of Python packages
RUN pip3 install --upgrade pip

# Install project dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install kibot
RUN pip3 install --no-compile kibot

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port to connect to website
EXPOSE 8000

# Run the Django development server
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]