#!/bin/bash

osc update rc pg-master --patch='{ "apiVersion": "v1beta1", "desiredState": { "replicas": 0 }}'
osc update rc pg-slave --patch='{ "apiVersion": "v1beta1", "desiredState": { "replicas": 0 }}'

osc delete rc pg-master
osc delete rc pg-slave

osc delete service pg-master
osc delete service pg-slave
