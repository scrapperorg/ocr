#/bin/bash

OUT_DIR="./logs"
mkdir -p ${OUT_DIR} && \
CONTAINER_ID=`docker compose ps -q` && \
LOG_PATH=`docker inspect --format='{{.LogPath}}' ${CONTAINER_ID}` && \
cp -f ${LOG_PATH} ${OUT_DIR} && \
echo "${OUT_DIR}/`basename ${LOG_PATH}`"
#docker compose pull && \
#docker compose up -d &&
echo "Done!"
