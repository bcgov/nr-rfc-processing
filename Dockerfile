FROM mambaorg/micromamba:1.4.3 as mamba
WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER explicit.lock /tmp/explicit.lock
COPY --chown=$MAMBA_USER:$MAMBA_USER requirements.txt /tmp/requirements.txt
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yaml /tmp/environment.yaml

RUN micromamba install --name base --yes --file /tmp/explicit.lock && \
    micromamba clean --all --yes

ARG MAMBA_DOCKERFILE_ACTIVATE=1
RUN python -m pip install -r /tmp/requirements.txt

# ------------------------------------------------------------------------------------
COPY --chown=$MAMBA_USER:$MAMBA_USER hatfieldcmr/ /app/hatfieldcmr/
COPY --chown=$MAMBA_USER:$MAMBA_USER admin /app/admin/
COPY --chown=$MAMBA_USER:$MAMBA_USER analysis /app/analysis/
COPY --chown=$MAMBA_USER:$MAMBA_USER aoi /app/aoi/
COPY --chown=$MAMBA_USER:$MAMBA_USER config /app/config/
COPY --chown=$MAMBA_USER:$MAMBA_USER download_granules /app/download_granules/
COPY --chown=$MAMBA_USER:$MAMBA_USER process /app/process/
COPY --chown=$MAMBA_USER:$MAMBA_USER snowpack_archive /app/snowpack_archive/
COPY --chown=$MAMBA_USER:$MAMBA_USER process /app/process/
COPY --chown=$MAMBA_USER:$MAMBA_USER ["run.py", "get_available_data.py", "/app/"]
