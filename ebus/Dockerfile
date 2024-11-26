# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install PostgreSQL client, Redis, and dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /ebus

# Copy the requirements file to the container
COPY requirements.txt ./

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Wait for postgres, run Django migrations, and start the Django development server
CMD ["/ebus/run.sh"]
