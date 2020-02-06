#!/usr/bin/env bash
set -eu
cd $(dirname $(readlink -f $0))

NS="foo bar blahblah"


for ns in ${NS};do
	kubectl delete pr --all || true
	kubectl delete tr --all || true
    kubectl create ns ${ns} 2>/dev/null || true
    
	for i in pipelinerun taskrrun task ;do
		kubectl -n ${ns} delete $i --all || true
	done

    kubectl -n ${ns} delete -f pipeline-randomwords.yaml -f pipeline-failmixed.yaml || true
    kubectl -n ${ns} create -f pipeline-randomwords.yaml -f pipeline-failmixed.yaml

    kubectl delete pr --all 2>/dev/null || true
    
	for i in {1..2};do
		tkn p -n ${ns} start pipeline-failmixed
		tkn p -n ${ns} start pipeline-randomwords
	done
done

    
