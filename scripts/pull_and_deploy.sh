#/bin/bash
git pull && \
docker compose pull && \
docker compose build && \
docker compose up -d && \
echo "Done!"
#sleep 5 
#&& \
#docker compose logs