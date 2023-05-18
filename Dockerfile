FROM mambaorg/micromamba:1.4.3
WORKDIR /app

COPY --chown=$MAMBA_USER:$MAMBA_USER explicit.lock /tmp/explicit.lock
COPY --chown=$MAMBA_USER:$MAMBA_USER hatfieldcmr/ /app/hatfieldcmr/

COPY ["setup.py",  "requirements.txt", "run.py", "get_available_data.py", "/app/"]
ARG MAMBA_DOCKERFILE_ACTIVATE=1

RUN ls -la && \
    micromamba create  -n snow_env -f /tmp/explicit.lock -y && \
    micromamba clean --all --yes && \
    eval "$(micromamba shell hook --shell=bash)" && \
    micromamba activate snow_env && \
    python -m pip install -r /app/requirements.txt



# ------------------------------------------------------------------------------------

COPY admin /app/admin/
COPY analysis /app/analysis/
COPY aoi /app/aoi/
COPY config /app/config/
COPY download_granules /app/download_granules/
COPY process /app/process/

COPY snowpack_archive /snowpack_archive/
COPY process /process/

RUN ls -la
ENV PATH=/opt/conda/envs/snow_env/bin:$PATH
ARG MAMBA_DOCKERFILE_ACTIVATE=1
# "/bin/micromamba", "activate", "snow_env", '&&'
ENTRYPOINT ["python", "run.py"]
CMD ["--help"]

