REPO=quay.io/chmouel
NAMESPACE=$(shell kubectl config view --minify --output 'jsonpath={..namespace}')

all: build push redeploy

build:
	docker build -t $(REPO)/collectlogs-operator -f Dockerfile.operator .
	docker build -t $(REPO)/collectlogs-frontend -f Dockerfile.frontend .

push:
	docker push $(REPO)/collectlogs-operator
	docker push $(REPO)/collectlogs-frontend

redeploy: SHELL:=/bin/bash   # HERE: this is setting the shell for b only
redeploy:
	@kubectl delete -f <(sed 's/%NAMESPACE%/$(NAMESPACE)/' kubernetes/deployment.yaml) 2>/dev/null || true
	@kubectl create -f <(sed 's/%NAMESPACE%/$(NAMESPACE)/' kubernetes/deployment.yaml) 2>/dev/null || true
