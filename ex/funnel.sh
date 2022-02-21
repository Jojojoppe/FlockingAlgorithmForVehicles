#!/bin/sh

for l in $(awk 'BEGIN{for(i=0;i<=100.0;i+=5){print i}}') ; do
    for ph in $(awk 'BEGIN{for(i=0.0;i<=1.0;i+=0.05){print i}}') ; do
        python3.8 main.py 0.26 1.5 1 $l $ph
    done
done
