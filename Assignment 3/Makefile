# Makefile for Docker commands

# Variables
NETWORK_NAME = assignment3_myNetwork
CONTROLLER_IMAGE_NAME = controller
WEB_SERVER_IMAGE_NAME = web-server
SHARD_MANAGER_IMAGE_NAME = shard-manager

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

############## Server tests #############

testbuild:
	docker build -t servertest Server

testrun:
	docker run --name servertest -p 5000:5000 servertest

teststop:
	docker stop servertest
	docker rm -f servertest

.PHONY: lbban serverban chal ruk testbuild testrun teststop