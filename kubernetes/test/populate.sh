#!/usr/bin/env bash
set -eu

NS="foo bar blahblah"


for ns in ${NS};do
    kubectl create ns ${ns} 2>/dev/null || true
    
    kubectl -n ${ns} delete -f pipeline-randomwords.yaml -f pipeline-failmixed.yaml 2>/dev/null || true
    kubectl -n ${ns} create -f pipeline-randomwords.yaml -f pipeline-failmixed.yaml

    kubectl delete pr --all 2>/dev/null || true
    
    tkn p -n ${ns} start pipeline-failmixed
    tkn p -n ${ns} start pipeline-randomwords
done

    
