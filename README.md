# OCR service

## Running as a docker container

### Running the latest release

```bash
# start services
docker compose -f docker-compose_release.yml up -d 
# close services
docker compose -f docker-compose_release.yml down 
```

### Building it from scratch

```bash
# build services
docker compose build 

# run services
docker compose up -d 

# stop services
docker compose down

# run tests
docker compose exec ocr bash -c "./scripts/run_tests.sh"
```



## Running locally
This code is not yet ready to be deployed in production.


### Create virtual env
```bash 
python3 -m venv .env
# load the env
source .env/bin/activate
```

### Install tesseract
```bash
apt-get update && apt-get install -y --no-install-recommends \
  software-properties-common gpg-agent
add-apt-repository -y ppa:alex-p/tesseract-ocr-devel
apt-get update && apt-get install -y --no-install-recommends \
  ghostscript \
  jbig2dec \
  img2pdf \
  libsm6 libxext6 libxrender-dev \
  pngquant \
  tesseract-ocr \
  tesseract-ocr-ron \
  unpaper
```

### Install OCRmyPDF
```bash
#
git clone  https://github.com/ocrmypdf/OCRmyPDF
cd /OCRmyPDF
pip install --no-cache-dir .
```

### Install API requirements
```bash 
# make sure you are in the root dir
cd ..
# basic dev requirements
pip install -r requirements.txt
# for running tests
pip install -r test_requirements.txt
# for running in production
pip install -r prod_requirements.txt
```

### Run API
```bash
# either run the script
./scripts/start-dev.sh

# or simply start
uvicorn --host localhost --port 8080 --log-level debug --log-config logging.ini api.api:app
```

### Run tests
```bash
# either run the script
./scripts/run_tests.sh

# runs flake8 to test python code standards
flake8 .

# and pytest unittests
pytest --cov-branch --cov-report term --cov-report html:coverage -rfExX --color=yes .
```
