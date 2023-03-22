#/bin/bash
set -e

OUTPUT_DIR=nlp/resources/

if [ -d "$OUTPUT_DIR" ];
then
    echo "Downloading models to: $OUTPUT_DIR"
else
	echo "$OUTPUT_DIR directory does not exist. Make sure you are in the root directory before running the script"
	exit 1
fi

cd $OUTPUT_DIR && \
rm -rf tessdata* && \
rm -rf ro_vocabulary* && \
wget https://github.com/scrapperorg/nlp-resources/files/10898263/tessdata.tar.gz && \
tar -xvf tessdata.tar.gz && \
rm tessdata.tar.gz && \
wget https://github.com/scrapperorg/nlp-resources/files/10898245/ro_vocabulary.tar.gz && \
tar -xvf ro_vocabulary.tar.gz && \
rm ro_vocabulary.tar.gz && \
python3 -m spacy download ro_core_news_sm