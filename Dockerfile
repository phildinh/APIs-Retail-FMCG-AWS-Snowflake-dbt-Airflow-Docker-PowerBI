# Start from the official Airflow image — same version your handover specifies
FROM apache/airflow:2.8.1

# Switch to root to install system-level dependencies if needed
USER root

# Switch back to the airflow user — always do this, never run Airflow as root
USER airflow

# Copy your requirements file into the image
COPY requirements.txt .

# Install your Python dependencies
# --no-cache-dir keeps the image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Install dbt-snowflake separately — pinned to match your dev environment
RUN pip install --no-cache-dir dbt-snowflake==1.7.2