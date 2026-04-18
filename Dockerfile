FROM condaforge/miniforge3:latest

WORKDIR /app

COPY environment.yaml .

RUN conda env create --file environment.yaml

COPY . .

ENV PATH="/opt/conda/envs/django/bin:$PATH"

EXPOSE 8000

CMD ["gunicorn", "springfield.wsgi", "--bind", "0.0.0.0:8000"]
