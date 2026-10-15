FROM condaforge/miniforge3:26.7.2-0

WORKDIR /app

COPY environment.yaml .

RUN mamba env create --file environment.yaml && mamba clean --all --yes

COPY . .

ENV PATH="/opt/conda/envs/django/bin:$PATH"

EXPOSE 8000

USER ubuntu

CMD ["gunicorn", "springfield.wsgi", "--bind", "0.0.0.0:8000"]
