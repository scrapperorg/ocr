# Based on OCRmyPDF
# SPDX-FileCopyrightText: 2022 James R. Barlow
# SPDX-License-Identifier: MPL-2.0

FROM ubuntu:22.04 as base

ENV LANG=C.UTF-8
ENV TZ=UTC
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

RUN apt-get update && apt-get install -y --no-install-recommends \
  python3 \
  libqpdf-dev \
  zlib1g \
  liblept5

FROM base as builder

# Note we need leptonica here to build jbig2
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential autoconf automake libtool \
  libleptonica-dev \
  zlib1g-dev \
  python3-dev \
  python3-distutils \
  libffi-dev \
  ca-certificates \
  curl \
  git

# Get the latest pip (Ubuntu version doesn't support manylinux2010)
RUN \
  curl https://bootstrap.pypa.io/get-pip.py | python3

# Compile and install jbig2
# Needs libleptonica-dev, zlib1g-dev
RUN \
  mkdir jbig2 \
  && curl -L https://github.com/agl/jbig2enc/archive/ea6a40a.tar.gz | \
  tar xz -C jbig2 --strip-components=1 \
  && cd jbig2 \
  && ./autogen.sh && ./configure && make && make install \
  && cd .. \
  && rm -rf jbig2


FROM base

# For Tesseract 5
RUN apt-get update && apt-get install -y --no-install-recommends \
  software-properties-common gpg-agent
RUN add-apt-repository -y ppa:alex-p/tesseract-ocr-devel

RUN apt-get update && apt-get install -y --no-install-recommends \
  ghostscript \
  jbig2dec \
  img2pdf \
  libsm6 libxext6 libxrender-dev \
  pngquant \
  tesseract-ocr \
  tesseract-ocr-ron \
  unpaper \
  && rm -rf /var/lib/apt/lists/*


COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

RUN apt-get update && apt-get install -y git curl wget

RUN git clone  https://github.com/ocrmypdf/OCRmyPDF
WORKDIR OCRmyPDF
RUN pip3 install --no-cache-dir .[test,webservice,watcher]


# RUN useradd -ms /bin/bash worker
# USER worker
# WORKDIR /home/worker

# RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
# ENV PATH="/root/.cargo/bin:${PATH}"
# pytokenizations


RUN mkdir -p /app
COPY . /app
WORKDIR /app

RUN pip3 install -r requirements.txt
RUN pip3 install -r test_requirements.txt

RUN echo "Downloading models..."
RUN ./scripts/pull_models.sh
RUN echo "Setting tesseract model..."
RUN cp nlp/resources/tessdata/* /usr/share/tesseract-ocr/5/tessdata/
