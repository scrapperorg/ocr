#/bin/bash
git pull && \
docker compose -f docker-compose_release.yml build && \
docker compose -f docker-compose_release.yml up -d && \
#sleep 5 
#&& \
#docker compose logs