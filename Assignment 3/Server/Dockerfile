# Use the official MySQL image as the base image
FROM mysql:8.0-debian

# COPY deploy.sh /always-initdb.d/
COPY ./deploy.sh /docker-entrypoint-initdb.d/deploy.sh

# Set environment variables for MySQL root password and database name
ENV MYSQL_ROOT_PASSWORD=password
ENV MYSQL_DATABASE=mydb
ENV MYSQL_USER=admin
ENV MYSQL_PASSWORD=password

RUN chmod 777 /docker-entrypoint-initdb.d/deploy.sh

# Install Python and pip
RUN apt-get update && apt-get install -y python3 python3-pip curl
RUN pip install flask --break-system-packages
RUN pip install mysql-connector-python --break-system-packages
RUN pip install requests --break-system-packages

# Copy the Flask application files to the container
COPY . /app

# Set the working directory in the container
WORKDIR /app

# Command to run the application
CMD ["mysqld"]
