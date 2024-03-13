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

# Install Python and pip and required packages
RUN apt-get update && apt-get install -y python3 python3-pip 
RUN pip install flask --break-system-packages
RUN pip install mysql-connector-python --break-system-packages

# Copy the Flask application files to the container
COPY . /app

# Set the working directory in the container
WORKDIR /app

RUN apt-get update && apt-get install -y sudo

RUN apt-get -y install apt-transport-https ca-certificates curl gnupg2 software-properties-common

# Install Docker
RUN curl https://get.docker.com/builds/Linux/x86_64/docker-latest.tgz | tar xvz -C /tmp/ && mv /tmp/docker/docker /usr/bin/docker

ENV USER=theuser
RUN adduser --home /home/$USER --disabled-password --gecos GECOS $USER \
  && echo "$USER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$USER \
  && chmod 0440 /etc/sudoers.d/$USER \
  && groupadd docker \
  && usermod -aG docker $USER \
  && chsh -s /bin/zsh $USER
USER $USER

ENV HOME=/home/$USER

# EXPOSE 5000:5000
EXPOSE 5000

CMD ["mysqld"]
