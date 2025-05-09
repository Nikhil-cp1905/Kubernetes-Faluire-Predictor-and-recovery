# Use an official lightweight Python image
FROM python:3.12-slim

# Set environment variables (better logging)
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create the models directory (fix missing folder issue)
RUN mkdir -p /app/models

# Copy application files from the root folder
COPY app.py /app/
COPY models/k8s_failure_model.pkl /app/models/k8s_failure_model.pkl

# Expose the FastAPI port
EXPOSE 8000

# Run the FastAPI app using Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

