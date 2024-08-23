# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the Python files into the container at /app
COPY *.py /app/

# Install any needed packages specified in requirements.txt
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5555 available to the world outside this container
EXPOSE 5555

# Run main.py when the container launches
CMD ["python", "main.py"]