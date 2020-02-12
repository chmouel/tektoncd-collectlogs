REPO=quay.io/chmouel
NAMESPACE := tekton-pipelines
TRIGGERS_URL := $(shell [[ -e .triggers-url ]] && cat .triggers-url)

all: build push

build:
	docker build -t $(REPO)/collectlogs-operator -f Dockerfile.operator .
	docker build -t $(REPO)/collectlogs-frontend -f Dockerfile.frontend .

push:
	docker push $(REPO)/collectlogs-operator
	docker push $(REPO)/collectlogs-frontend

# Will deploy cluster-admin (so what everything in cluster)
redeploy-cluster: SHELL:=/bin/bash
redeploy-cluster:
	@kubectl delete -f <(sed 's/%NAMESPACE%/$(NAMESPACE)/' kubernetes/deployment.yaml kubernetes/sa-cluster.yaml ) 2>/dev/null || true
	@kubectl create -f <(sed 's/%NAMESPACE%/$(NAMESPACE)/' kubernetes/deployment.yaml kubernetes/sa-cluster.yaml )
	@kubect get route 2> /dev/null  >/dev/null || true && \
		kubectl delete -f <(sed "s/%NAMESPACE%/$(NAMESPACE)/" kubernetes/openshift-route.yaml) 2>/dev/null || true && \
		kubectl create -f <(sed "s/%NAMESPACE%/$(NAMESPACE)/" kubernetes/openshift-route.yaml)


# Will deploy scoped to the current cluster (so current namespace)
redeploy-scoped: SHELL:=/bin/bash   # HERE: this is setting the shell for b only
redeploy-scoped:
	@set -x && namespace=$(shell kubectl config view --minify --output 'jsonpath={..namespace}') && \
		kubectl delete -f <(sed "s/%NAMESPACE%/$$namespace/" kubernetes/deployment.yaml kubernetes/sa-scoped.yaml) 2>/dev/null || true && \
		kubectl create -f <(sed "s/%NAMESPACE%/$$namespace/" kubernetes/deployment.yaml kubernetes/sa-scoped.yaml) && \
		kubectl set env deployment/collectlogs -c operator TARGET_NAMESPACE="$$namespace" && \
		[[ "X$(TRIGGERS-URL)" != X ]] && \
			kubectl set env deployment/collectlogs -c operator TRIGGERS_URL=$(TRIGGERS_URL) && \
		kubect get route 2> /dev/null  >/dev/null || true && \
		kubectl delete -f <(sed "s/%NAMESPACE%/$$namespace/" kubernetes/openshift-route.yaml) 2>/dev/null || true && \
		kubectl --validate=false create -f <(sed "s/%NAMESPACE%/$$namespace/" kubernetes/openshift-route.yaml)
