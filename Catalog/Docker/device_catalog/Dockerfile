FROM python:3.9.16-slim
WORKDIR /SICU
COPY Catalog /SICU/Catalog
RUN pip install --no-cache-dir -r /SICU/Catalog/requirements.txt && \
    rm -rf ~/.cache/pip
CMD ["python", "-m", "Catalog.device_catalog"]