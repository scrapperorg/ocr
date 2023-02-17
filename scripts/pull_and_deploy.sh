#/bin/bash
git pull && \
docker pull readable/ocr:main && \
docker compose -f docker-compose_release.yml build && \
docker compose -f docker-compose_release.yml up -d && \
echo "Done!"
#sleep 5 
#&& \
#docker compose logs