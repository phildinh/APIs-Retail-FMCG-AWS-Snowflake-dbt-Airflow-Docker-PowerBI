FROM python:3.11-slim

# system dependencies needed by snowflake connector and dbt
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# set working directory inside the container
WORKDIR /app

# copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install dbt with snowflake adapter
RUN pip install --no-cache-dir \
    dbt-core==1.7.4 \
    dbt-snowflake==1.7.1

# copy the rest of the project
COPY . .

# default command - can be overridden by docker-compose or Airflow
CMD ["python", "-m", "ingestion.pipeline"]