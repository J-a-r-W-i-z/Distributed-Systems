# Makefile for Docker commands

# Variables
NETWORK_NAME = assignment2_myNetwork
CONTROLLER_IMAGE_NAME = controller
WEB_SERVER_IMAGE_NAME = web-server

# Targets and Rules

lbban:
	docker build -t $(CONTROLLER_IMAGE_NAME) ./"Load Balancer"

serverban:
	docker build -t $(WEB_SERVER_IMAGE_NAME) ./Server

chal:
	docker compose up

ruk:
	docker ps -q --filter network=$(NETWORK_NAME) | xargs -r docker stop
	docker ps -aq --filter network=$(NETWORK_NAME) | xargs -r docker rm
	docker compose down

.PHONY: lbban serverban chal ruk