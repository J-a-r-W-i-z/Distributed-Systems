# Dockerfile
FROM python:3.8-slim

WORKDIR /app

COPY shard_manager.py .

RUN apt-get update && apt-get install -y sudo

RUN apt-get -y install apt-transport-https ca-certificates curl gnupg2 software-properties-common

RUN curl https://get.docker.com/builds/Linux/x86_64/docker-latest.tgz | tar xvz -C /tmp/ && mv /tmp/docker/docker /usr/bin/docker

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

CMD ["python", "-u", "shard_manager.py"]
