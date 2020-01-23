REPO=quay.io/chmouel

all: build push

build:
	docker build -t $(REPO)/collectlogs-operator -f Dockerfile.operator .
	docker build -t $(REPO)/collectlogs-frontend -f Dockerfile.frontend .

push:
	docker push $(REPO)/collectlogs-operator
	docker push $(REPO)/collectlogs-frontend
