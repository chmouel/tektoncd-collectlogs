#!/usr/bin/env bash
set -eu
cd $(dirname $(readlink -f $0))

NS="foo bar blahblah"


for ns in ${NS};do
    kubectl create ns ${ns} 2>/dev/null || true
    
    kubectl -n ${ns} delete -f pipeline-randomwords.yaml -f pipeline-failmixed.yaml 2>/dev/null || true
    kubectl -n ${ns} create -f pipeline-randomwords.yaml -f pipeline-failmixed.yaml

    kubectl delete pr --all 2>/dev/null || true
    
	for i in {1..10};do
		tkn p -n ${ns} start pipeline-failmixed
		tkn p -n ${ns} start pipeline-randomwords
	done
done

    
