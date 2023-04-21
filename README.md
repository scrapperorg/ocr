# OCR service

## Contents
- [JSON Response](#response)

## Running as a docker container

### Pre-requisites

Currently there are several environment variables that have to be set before the docker container starts.
These can be set in `docker-compose.yml` environment section:

- WORKER_ID=1 - Can be set to any value that can identify the worker, in cases when there are multiple workers spawned.
- OUTPUT_PATH=/storage - A path that is accessible by the worker to be used to write the output PDF files.
- SLEEP_TIME=10 - This is the amount of seconds to sleep when encountering an error or when no more documents are left to be processed.
- LOG_LEVEL=INFO -Log level, recommended to be INFO
- MAX_NUM_PAGES=2000 - Maximum document length to process. Otherwise will return failure. This is more of a safety parameter to avoid ingesting documents if very large sizes. If not set, by default is `75600` the time to process a document for one week `75600*8 / 60/60/24` with one CPU (8 seconds per page).
- NUM_PROC=2 Number of parallel processes to run jobs on. If the container has more than one CPU available, this could drastically increase performance.
- API_ENDPOINT=http://{} - Represents the endpoint that feeds the worker with documents.
- SPACY_MODEL=ro_legal_fl - default is custom floret legal embeddings; used for word representations and for lemmatization; can be anything from [here](https://spacy.io/models/ro)
- VECTOR_SEARCH=True - if enabled, it will highlight with blue semantic similarly phrases


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

<a name="response"></a>

<details>
<summary><i>Show json response</i></summary>

```json
{
    "worker_id": 1,
    "id": "3b4d634d-8616-4809-9c68-2e2c923d1e1a",
    "status": "ocr_done",
    "message": "",
    "analysis":
            {
            "worker_version": "0.5.2",
            "input_file": "nlp/documents//normal.pdf",
            "ocr_file": "nlp/documents/normal/normal_ocr.pdf",
            "ocr_quality": 96.25,
            "text_file": "nlp/documents/normal/normal_ocr.txt",
            "text": "..(to be deprecated)..",
            "statistics": {
                "num_pages": 3,
                "num_ents": 0,
                "num_kwds": 3,
                "num_wds": 988
            },
            "highlight_file": "nlp/documents/normal/normal_highlight.pdf",
            "highlight_metadata": [
                {
                    "keyword": "proiect",
                    "occs": [
                        {
                            "page": 0,
                            "location": {
                                "x1": 366.0708923339844,
                                "x2": 394.4169921875,
                                "y1": 641.0471801757812,
                                "y2": 652.0478515625
                            }
                        }
                    ],
                    "total_occs": 1
                },
                {
                    "keyword": "termen",
                    "occs": [
                        {
                            "page": 2,
                            "location": {
                                "x1": 379.7745361328125,
                                "x2": 406.9278259277344,
                                "y1": 114.33213806152344,
                                "y2": 125.33673095703125
                            }
                        }
                    ],
                    "total_occs": 1
                },
                {
                    "keyword": "produse",
                    "occs": [
                        {
                            "page": 2,
                            "location": {
                                "x1": 151.5498809814453,
                                "x2": 183.67770385742188,
                                "y1": 214.6649169921875,
                                "y2": 226.669921875
                            }
                        }
                    ],
                    "total_occs": 1
                }
            ],
            "processing_time": 7.217
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
./scripts/download_pdfs.sh

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
