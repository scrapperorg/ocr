# Changelog
Adding notes to what is being changed from time to time

## [1.1.0] 31.05.2023
### Added
- summarization when payload fails
- type annotations to functions
### Changed
- code cleaning so that env variables are in a single file
### Removed
- web API
- web dependencies

## [1.0.1] 17.05.2023
### Changed
- fix issue with span_ruler pipe when already there
- improved robustness when keywords loading fails

## [1.0.0] 09.05.2023
### Added
- reading keywords from next-document response
### Changed
- ro_legal as default model
- context on full keyword


## [0.6.3] 10.04.2023
### Added
- `en_core_ro_lg` as alternative model
- synonym expansion from Romanian WordNet
- for each synonym, a cosine similarity filtering is used to compare against the context vector of each word
- params to enable / disable Vector Search and synonyms
- VectorSearcher using nsmlib failed with core dumped - changed into OneClassSVM
- introduced number of characters in the statistics
- text cleaner pre-processor to clean the raw text documents



## [0.5.3] 10.04.2023
### Added
- improved matching to use both lemma and lowercase form of words
- enabled by default option to dump text file
- option to dump json for statistics and debugging
- more test cases for a PDF containing all keywords
- improved robustness to rotated pages
- if quality below a threshold, attempts again with more aggressive rotation
- changed logging for OOV words in quality estimation


## [0.5.2] 08.04.2023
### Added
- number of jobs fixed to environment variable (default 1)
- introduced auto-rotate for documents
- increased tesseract timeout per page
- generate PDF instead of PDF/A for docs larger than 50 pages
- added option to limit the total number of pages to do OCR
- added CPU and memory limitation to container in docker-compose.yml
- simplified function to set ocrmypdf parameters
- validate document in performance testing
- raw tests on several types of files
- fixed bug when generated PDF was not valid (strange_error.pdf)

## [0.4.0] 07.04.2023
### Added
- safety feature for encrypted or digitally signed pdfs
- attempts to overwrite the original file, if encrypted

## [0.3.5] 07.04.2023
### Added
- better logging to avoid repeated similar messages
- version in the app and in the logs
- LOG_LEVEL variable in the environment
- separated github build and push and deploy workflows
- raise for error when server errors occur [500 - 600]

## [0.2.8] 03.04.2023
### Added
- performance test script that generates stats for each file
- option to load and download ro_legal_fl model
- statistics in the output
- pipeline fixes
- stop auto-deploy of API service
- performance tests with docker-compose.yml
- pre-commit hook configuration


## [0.1.1] 22.03.2023
### Added
- smarter keyword matching using lemmatization
- added annotation to the original keyword in the highligh
- parameter to dump information into a json file
- test that runs the whole analysis
- option to underline Named Entities


## [Unreleased] 16.03.2023
### Added
- dependencies and ML models in docker container
- added custom Tesseract model and external resources
- if custom Tesseract model is missing, fail-back on default


## [Unreleased] 15.03.2023
### Added
- highlight keywords
### Changed
- pipeline and docker-compose to use ocr:latest


## [Unreleased] 08.03.2023
### Added
- example file to run tests
- prepare Dockerfile commands to install rust
### Changed
- text is being returned from blocks instead of raw text
- cleaned worker
