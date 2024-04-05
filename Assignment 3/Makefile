# Makefile for Docker commands

# Variables
NETWORK_NAME = assignment2_myNetwork
CONTROLLER_IMAGE_NAME = controller
WEB_SERVER_IMAGE_NAME = web-server
SHARD_MANAGER_IMAGE_NAME = shardmanager

# Targets and Rules

lb:
	docker build -t $(CONTROLLER_IMAGE_NAME) ./"Load Balancer"

server:
	docker build -t $(WEB_SERVER_IMAGE_NAME) ./Server

shardmanager:
	docker build -t ${SHARD_MANAGER_IMAGE_NAME} ./"Shard Manager"

run:
	docker compose up

stop:
	docker ps -q --filter network=$(NETWORK_NAME) | xargs -r docker stop
	docker ps -aq --filter network=$(NETWORK_NAME) | xargs -r docker rm
	docker compose down

.PHONY: lbban serverban chal ruk