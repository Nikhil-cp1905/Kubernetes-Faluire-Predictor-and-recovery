
# DEPLOYMENTS AND HOW TO USE IT (PLEASE READ)
[!]https://docs.google.com/document/d/1R6nR_AweptKE9sJPMdnFxIeO3jDxQfkfBhI2Ld4GCDc/edit?usp=sharing


BRAND NEW CHATBOT UI
[!]https://k8chatbot.vercel.app/


[!]https://docs.google.com/presentation/d/1fE-f3UlMdvPvwsPu7tjNVFxIesq9U5uNW-DJhCRIQb4/edit?usp=sharing


# LATEST UPDATE!!!!!!!!!
FOR THE FRONTEND OF GEMINI LOGGING, A USER CAN SEE IT BEAUTIFULLY WITH A WELL
UI. To know more, see below- 
To run the backend for the gemini remediation and advice setup
```bash
python3 src/server.py
```

To run the frontend
```bash
cd frontend/k8s-remediation-dashboard/src
```
```bash
npm run dev
```

See below for the screenshots-
![Image](https://github.com/user-attachments/assets/19a70204-43ba-4817-b987-b6b35c7e373f)

![Image](https://github.com/user-attachments/assets/ef44afe6-53bd-4f95-858c-f2a2ce6742c9)

![Image](https://github.com/user-attachments/assets/f337ae1f-d779-47cd-9f81-d9a3b96f0f86)
Downloadable-
![Image](https://github.com/user-attachments/assets/8c1888d4-c472-40c6-baa5-1f02c6ee3202)


(PLEASE NOTE- The data is being scraped from prometheus EVERY 5 MINUTES. Model will be best trained with time.)

The vercel app is for the frontend (additional feature) and does not really come under the model training and gemini output.
We used prometheus in kubernetes using minikube to scrape the data. We tried to make it a public IP but due to security constraints and few free tier cloud options, we decided to keep it local.
If needed, you can run it on your own prometheus and dataset (through src/fetch_live_metrics and data/k8s_live_metrics.csv)
The model is under models/k8s_failure_model_live.pkl
This has been deployed online. 
The gemini output and remediation step is under src/predictgemini.py src/jsonextractor.py .(predictgeministreamlit.py was for testing to integrate with streamlit)
ALL OF THIS BEAUTIFULLY COMES TOGETHER IN 
streamlitapp.py in the root directory 

(PLEASE NOTE- IT WORKS WITH LOCAL IP, WE COULD NOT RUN PROMETHEUS GLOBALLY AS MENTIONED. BUT PLEASE TRY IT OUT. HENCE THE FETCH METRICS IS WITH THE CURRENT SMALL AMOUNT OF DATA)

Read below to know more about our project.

# Kubernetes Failure Prediction

This project aims to build a machine learning model for predicting Kubernetes cluster failures using real-time and historical cluster metrics. The goal is to identify potential issues in a Kubernetes environment, such as pod/node failures, resource exhaustion, and network issues, before they occur. 

The system leverages a variety of tools and libraries, including Prometheus for metrics collection, Python for data processing, and machine learning algorithms to predict failures.

## Table of Contents

- [Project Overview](#project-overview)
- [System Requirements](#system-requirements)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [Model Evaluation](#model-evaluation)
- [Deployment](#deployment)
- [Testing](#testing)
- [Licenses](#licenses)

## Project Overview

Kubernetes clusters can face a variety of issues, from pod/node failures to resource exhaustion or network issues. Predicting these failures in advance can help maintain a more stable and efficient cluster. This project includes:

1. Data collection from Kubernetes clusters.
2. Feature engineering to prepare metrics for machine learning.
3. Training of a machine learning model to predict failures.
4. Deployment of the model in a Kubernetes environment.
5. Evaluation and visualization of the model's performance.

## System Requirements

- **Python 3.7+**
- **Prometheus** (for fetching live Kubernetes metrics)
- **Docker** (for containerizing the application)
- **Kubernetes** (for deployment)
- **Machine Learning Libraries**: `scikit-learn`, `pandas`, `numpy`, `matplotlib`, `joblib`, etc.

## Project Structure

```plaintext
kubernetes-failure-prediction/
├── src/                         # Code for data collection, model training, and evaluation
│   ├── deployment.yaml          # Kubernetes deployment configuration
│   ├── generate_output.py       # Generates model output for analysis
│   ├── __pycache__/             # Compiled Python files
│   ├── feature_engineering.py   # Script for feature engineering
│   ├── jsonextractor.py         # Extracts JSON data for processing
│   ├── test_model.py            # Tests for evaluating model performance
│   └── external_data_link.txt    # External link to large datasets
├── docs/                         # Documentation files
│   └── README.md                 # This file
├── presentation/                 # Slides and recorded demo (YouTube/Drive link)
│   ├── slides.pptx               # Slides for the presentation
│   └── demo_link.txt             # Link to recorded demo (YouTube/Google Drive)
├── deployment/                   # Files for deploying the model to Kubernetes
│   ├── kubernetes_deploy.yaml    # Kubernetes deployment configuration
│   └── Dockerfile                # Dockerfile for containerizing the model
├── tests/                        # Unit and integration tests
├── requirements.txt              # Python dependencies
└── LICENSE                       # License information
```

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/kubernetes-failure-prediction.git
cd kubernetes-failure-prediction
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up Prometheus

Ensure that you have Prometheus running and that it's scraping Kubernetes metrics. You can set up Prometheus as per [Kubernetes documentation](https://prometheus.io/docs/prometheus/latest/getting_started/).

## Usage

### 1. Collect Metrics

You can collect Kubernetes metrics by running:

```bash
python src/fetch_live_metrics.py
```

This will fetch live metrics from your Prometheus instance.

### 2. Train the Model

To train the model on your dataset, use the following command:

```bash
python src/train_model_live.py
```

This will train the model on the collected data and output the trained model as `failure_predictor.pkl` in the `models/` directory.

### 3. Predict Failures

Once the model is trained, you can use it to predict failures in your Kubernetes cluster:

```bash
python src/predictgemini.py
```

This script will load the trained model and predict potential failures based on real-time metrics.

## Model Evaluation

To evaluate the model's performance, use the following script:

```bash
python src/test_model.py
```

This will test the model on a test dataset and display evaluation metrics such as accuracy, precision, recall, and F1 score.

## Deployment

### 1. Dockerize the Application

Use the Dockerfile to containerize the application:

```bash
docker build -t k8s-failure-prediction .
```

### 2. Deploy to Kubernetes

You can deploy the model using the Kubernetes configuration in `deployment.yaml`:

```bash
kubectl apply -f deployment.yaml
```

This will deploy your model to a Kubernetes cluster. Make sure that your cluster has access to the necessary metrics from Prometheus.

## Testing

Unit and integration tests are located in the `tests/` directory. To run the tests, use:

```bash
pytest tests/
```

This will run all the unit and integration tests to ensure the code is working as expected.

## Licenses
This will run all the unit and integration tests to ensure the code is working as expected.

This will run all the unit and integration tests to ensure the code is working as expected.

This will run all the unit and integration tests to ensure the code is working as expected.

## Licenses

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Prometheus](https://prometheus.io/) for real-time metrics collection.
- [scikit-learn](https://scikit-learn.org/stable/) for machine learning algorithms.
- [Kubernetes](https://kubernetes.io/) for orchestration and deployment.

Feel free to contribute to the project or suggest improvements via issues and pull requests. Happy coding!

```
