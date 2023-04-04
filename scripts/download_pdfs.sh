#/bin/bash

set -e

DEST="nlp/corpus"
BASE_URL="https://github.com/senisioi/rolegal/releases/download/raw_pdf_v1/"
mkdir -p ${DEST} && \
rm -f ${DEST}/senat.tar.gz* && \
wget ${BASE_URL}/senat.tar.gz -P ${DEST} && \
wget ${BASE_URL}/cdep_senat.tar.gz -P ${DEST} && \
wget ${BASE_URL}/cdep.tar.gz -P ${DEST} && \
tar -xvf ${DEST}/senat.tar.gz -C ${DEST} && \
tar -xvf ${DEST}/cdep_senat.tar.gz && \
tar -xvf ${DEST}/cdep.tar.gz
