FROM continuumio/miniconda3:4.9.2-alpine AS build

COPY hatfieldcmr /hatfieldcmr/
COPY setup.py /setup.py
COPY requirements-conda.txt /requirements-conda.txt
RUN conda update -y conda && \
    conda config --add channels conda-forge && \
    conda config --add channels anaconda && \
    conda create -y --name process python=3.9 && \
    conda install -n process -y --file requirements-conda.txt

RUN conda install -c conda-forge conda-pack && \
    conda-pack -n process -o /tmp/env.tar && \
    mkdir /venv && cd /venv && tar xf /tmp/env.tar && \
    rm /tmp/env.tar && \
    /venv/bin/conda-unpack

FROM ubuntu:20.04 AS runtime
COPY --from=build /venv /venv

COPY hatfieldcmr /app/hatfieldcmr/
COPY requirements.txt app/requirements.txt
COPY admin /app/admin/
COPY analysis /app/analysis/
COPY aoi /app/aoi/
COPY download_granules /app/download_granules/
COPY process /app/process/
COPY run.py /app/run.py
COPY setup.py app/setup.py

ENV PATH=/venv/bin:$PATH

WORKDIR /app
RUN pip install -e .
ENTRYPOINT ["python", "run.py"]
CMD ["--help"]
