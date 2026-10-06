FROM condaforge/miniforge3:26.1.1-3

WORKDIR /app

COPY environment.yaml .

RUN conda env create --file environment.yaml

COPY . .

ENV PATH="/opt/conda/envs/django/bin:$PATH"

RUN useradd --create-home --uid 1000 app

USER app

EXPOSE 8000

CMD ["gunicorn", "springfield.wsgi", "--bind", "0.0.0.0:8000"]
