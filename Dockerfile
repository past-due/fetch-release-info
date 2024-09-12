FROM python:3-slim AS build-env
COPY . /app
WORKDIR /app

# We are installing dependencies here directly into our app source dir
RUN pip install --target=/app -r requirements.txt

# A distroless container image with Python and some basics like SSL certificates
# https://github.com/GoogleContainerTools/distroless
FROM gcr.io/distroless/python3
COPY --from=build-env /app /app
WORKDIR /app
ENV PYTHONPATH /app
CMD ["/app/main.py"]
