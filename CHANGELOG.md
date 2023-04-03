# Changelog
Adding notes to what is being changed from time to time

## [0.2.0] 03.04.2023
### Added
- performance test script
- option to load ro_legal_fl model
- statistics in the output

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