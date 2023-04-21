#!/bin/bash

for DATASET in guo du
do
  echo dataset ${DATASET}
  { time dscript train --train data/original/${DATASET}_train.txt --test data/original/${DATASET}_test.txt --embedding /nfs/scratch/jbernett/yeast_embedding.h5 --save-prefix ./models/${DATASET}_dscript_model -o ./results_dscript/original/${DATASET}_train.txt -d 0; } 2> results_dscript/original/${DATASET}_time.txt
  { time dscript train --topsy-turvy --train data/original/${DATASET}_train.txt --test data/original/${DATASET}_test.txt --embedding /nfs/scratch/jbernett/yeast_embedding.h5 --save-prefix ./models/${DATASET}_tt_model -o ./results_topsyturvy/original/${DATASET}_train.txt -d 0; } 2> results_topsyturvy/original/${DATASET}_time.txt
done
