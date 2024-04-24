#!/bin/bash

params_array=("" "4 7" "6 8 10")

for i in {1..3}; do
    params="${params_array[$i - 1]}"

    make run &
    sleep 30
    python3 Analysis/client.py $i $params
    make stop
    sleep 10
done
