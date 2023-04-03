# OCR service

## Running as a docker container

### Pre-requisites

Currently there are several environment variables that have to be set before the docker container starts.
These can be set in `docker-compose.yml` environment section:

##### WORKER_ID=1
Can be set to any value that can identify the worker, in cases when there are multiple workers spawned.

##### OUTPUT_PATH=/storage
A path that is accessible by the worker to be used to write the output PDF files.

##### SLEEP_TIME=10
This is the amount of seconds to sleep when encountering an error or when no more documents are left to be processed.

##### API_ENDPOINT=http://{}
Represents the endpoint that feeds the worker with documents.
The HTTP server must implement two endpoints `/next-document` to return a document of the following form:
```json
{
    "id": "3b4d634d-8616-4809-9c68-2e2c923d1e1a",
    "storagePath":  "/opt/storage/3b4d634d-8616-4809-9c68-2e2c923d1e1a.pdf",
    "status": "downloaded"
}
```
- depending on the status of the document, the worker might process or skip the doc
- ! one must ensure that the `storagePath` provided through the API is accessible by the worker

And `/ocr-updates` where the worker will post the results of the document processing.
An example body response is here:

<details>
<summary><i>Show json response</i></summary>

```json
{
    "worker_id": 1,
    "id": "3b4d634d-8616-4809-9c68-2e2c923d1e1a",
    "status": "ocr_done",
    "message": "",
    "analysis": {
        "input_status": "downloaded",
        "input_file": "nlp/documents/3b4d634d-8616-4809-9c68-2e2c923d1e1a.pdf",
        "ocr_file": "nlp/documents/analysis/3b4d634d-8616-4809-9c68-2e2c923d1e1a_ocr.pdf",
        "text": "...",
        "ocr_quality": 95.63,
        "highlight_file": "nlp/documents/analysis/3b4d634d-8616-4809-9c68-2e2c923d1e1a_highlight.pdf",
        "highlight_metadata": [
            {
                "keyword": "Guvern",
                "occs": [
                    {
                        "page": 0,
                        "location": {
                            "x1": 373.2699890136719,
                            "x2": 398.5975036621094,
                            "y1": 157.97280883789062,
                            "y2": 166.973388671875
                        }
                    },
                    {
                        "page": 0,
                        "location": {
                            "x1": 389.4679870605469,
                            "x2": 425.0047302246094,
                            "y1": 262.2874755859375,
                            "y2": 275.288330078125
                        }
                    },
                    {
                        "page": 0,
                        "location": {
                            "x1": 463.6180114746094,
                            "x2": 491.4978332519531,
                            "y1": 438.09368896484375,
                            "y2": 449.0943603515625
                        }
                    },
                    {
                        "page": 1,
                        "location": {
                            "x1": 340.6679992675781,
                            "x2": 369.3157653808594,
                            "y1": 737.9363403320312,
                            "y2": 749.9359741210938
                        }
                    }
                ],
                "total_occs": 4
            }
        ]
    }
}
```
</details>

The possible statuses of a document are:
```python
class Statuses:
    "downloaded"
    "locked"
    "ocr_in_progress"
    "ocr_done"
    "ocr_failed"
    "not_found"
```

### Starting the container
Once these environment variables have been set, one can simply start the container using:
```bash
# make sure to pull the latest changes
docker compose pull
# start services
docker compose up -d
# close services
docker compose down
```

### Building it from scratch

```bash
# either via docker build
docker build -t readable/ocr:main -f ./Dockerfile .

# or via docker compose
# build services
docker compose -f docker-compose_dev.yml build

# run services
docker compose -f docker-compose_dev.yml up -d

# stop services
docker compose -f docker-compose_dev.yml down

# run tests
docker compose -f docker-compose_dev.yml exec ocr bash -c "./scripts/run_tests.sh"
```



## Installing locally on the host OS
The following steps are valid for an **Ubuntu** system.

### Create virtual env
```bash
python3 -m venv .env
# load the env
source .env/bin/activate
```

### Install pre-commit hooks
```bash
pip install pre-commit
pre-commit install
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

### Install app requirements
```bash
# make sure you are in the root dir
cd ..

# basic dev requirements
pip install -r requirements.txt

# for running tests
pip install -r test_requirements.txt
```

### Download models
```bash
# download models to nlp/resources
./scripts/pull_models.sh

# copy tesseract model to TESSDATA dir
cp nlp/resources/tessdata/* /usr/share/tesseract-ocr/5/tessdata/
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

### Run performance test
```bash
# 1. get a dataset to run the performance test on
mkdir -p corpus/
wget https://github.com/senisioi/rolegal/releases/download/raw_pdf_v1/senat.tar.gz -P corpus/
wget https://github.com/senisioi/rolegal/releases/download/raw_pdf_v1/cdep_senat.tar.gz -P corpus/
wget https://github.com/senisioi/rolegal/releases/download/raw_pdf_v1/cdep.tar.gz -P corpus/
cd corpus && tar -xvf senat.tar.gz && tar -xvf cdep_senat.tar.gz && tar -xvf cdep.tar.gz && cd ..

# 2. run the performance test
docker compose -f docker-compose_perf.yml pull && \
docker compose -f docker-compose_perf.yml up -d

docker compose -f docker-compose_perf.yml logs
```


### Run API
API is currently for testing purposes.
```bash
# either run the script
./scripts/start-dev.sh

# or simply start
uvicorn --host localhost --port 8080 --log-level debug --log-config logging.ini api.api:app
```
