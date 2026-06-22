# Use the latest stable Airflow version with the recommended Python version
FROM apache/airflow:slim-2.10.4-python3.12

USER root
# Include github token as build arg from .env, so we can access pawdb and pawfs repos
ARG GITHUB_TOKEN

# Install system dependencies required for Python
RUN apt-get update && apt-get install -y \
    curl \
    python3-venv \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


# Switch back to airflow user
USER airflow
RUN pip install --upgrade pip


# Set Airflow version and Python version for constraints
ENV CONSTRAINT_URL=https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt

# Install this monorepo's dependencies from requirements files with Airflow constraints
COPY ./packages/template_package/requirements.txt /tmp/template_package_requirements.txt
RUN pip install --no-cache-dir --constraint "${CONSTRAINT_URL}" -r /tmp/template_package_requirements.txt

# Set the working directory
WORKDIR /usr/local/airflow

# Expose the necessary ports
EXPOSE 8080

# Start the Airflow web server by default
CMD ["airflow", "webserver"]