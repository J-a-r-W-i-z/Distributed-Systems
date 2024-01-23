# Dockerfile
FROM python:3.8-slim

WORKDIR /app

COPY load_balancer.py .

RUN apt-get update && apt-get install -y sudo

RUN apt-get -y install apt-transport-https ca-certificates curl gnupg2 software-properties-common

# # Add Docker GPG key
# RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# # Add Docker repository
# RUN echo "deb [signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# # Install Docker
# RUN apt-get update
# RUN apt-get -y install docker-ce-cli
RUN curl https://get.docker.com/builds/Linux/x86_64/docker-latest.tgz | tar xvz -C /tmp/ && mv /tmp/docker/docker /usr/bin/docker

# Customize here your container...

RUN pip install requests

ENV USER=theuser
RUN adduser --home /home/$USER --disabled-password --gecos GECOS $USER \
  && echo "$USER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$USER \
  && chmod 0440 /etc/sudoers.d/$USER \
  && groupadd docker \
  && usermod -aG docker $USER \
  && chsh -s /bin/zsh $USER
USER $USER

ENV HOME=/home/$USER

# EXPOSE 5500:5500
EXPOSE 5000

CMD ["python", "-u", "load_balancer.py"]
