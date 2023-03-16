# Changelog
Adding notes to what is being changed from time to time

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