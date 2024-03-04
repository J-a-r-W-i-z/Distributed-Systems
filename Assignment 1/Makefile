# Makefile for Docker commands

# Variables
NETWORK_NAME = assignment1_myNetwork
CONTROLLER_IMAGE_NAME = controller
WEB_SERVER_IMAGE_NAME = web-server

# Targets and Rules

build:
	docker build -t $(CONTROLLER_IMAGE_NAME) ./"Load Balancer"
	docker build -t $(WEB_SERVER_IMAGE_NAME) ./Server

run:
	docker compose up

stop:
	docker ps -q --filter network=$(NETWORK_NAME) | xargs -r docker stop

clean:
	docker ps -aq --filter network=$(NETWORK_NAME) | xargs -r docker rm
	docker compose down

.PHONY: build-controller build-server run stop clean
