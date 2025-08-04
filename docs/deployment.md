# Deployment Guide

This guide provides instructions on how to package your model wrapper service into a Docker container for deployment.

## Docker Packaging

Packaging your service with Docker allows you to create a portable and reproducible environment for your model.

### 1. Create a `Dockerfile`

Create a `Dockerfile` in the root of your project. This file will contain the instructions for building your Docker image. You can use the `Dockerfile` in this repository as a starting point.

A typical `Dockerfile` for a Python application will:
1.  Start from a Python base image.
2.  Set a working directory.
3.  Copy your project's requirements file and install the dependencies.
4.  Copy the rest of your project's code into the image.
5.  Define the command to run your service when the container starts.

### 2. Build the Docker Image

Once you have created your `Dockerfile`, you can build the Docker image using the following command:

```bash
docker build -t your-image-name:your-tag .
```
Replace `your-image-name` and `your-tag` with a name and tag for your image (e.g., `my-solubility-predictor:v1`).

### 3. Run the Docker Container

After building the image, you can run it as a container:

```bash
docker run -p 8080:8080 your-image-name:your-tag
```
This will start your service and map port 8080 on your local machine to port 8080 in the container. You can then access your service at `http://localhost:8080`.

### 4. Push to a Container Registry

To use your image in a production environment, you will need to push it to a container registry, such as Docker Hub, Google Container Registry (GCR), or Amazon Elastic Container Registry (ECR).

```bash
docker push your-registry/your-image-name:your-tag
```

## Kubernetes Deployment with Helm

For deploying your service to a Kubernetes cluster, we recommend using the [OpenAD Model Helm Template](https://github.com/acceleratedscience/openad-model-helm-template). This Helm chart provides a standardized way to deploy OpenAD models to Kubernetes and OpenShift.

Please refer to the documentation in the [OpenAD Model Helm Template repository](https://github.com/acceleratedscience/openad-model-helm-template) for detailed instructions on how to use the chart.
