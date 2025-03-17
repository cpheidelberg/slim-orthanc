FROM jodogne/orthanc-plugins:latest

RUN apt-get update && apt-get install -y libopenslide0 libopenslide-dev

RUN apt-get install -y libgdcm-dev libdcmtk-dev libjpeg-dev libpng-dev libtiff-dev

# Erstelle das Konfigurationsverzeichnis
RUN mkdir -p /run/secrets
COPY orthanc.json /run/secrets/orthanc.json

CMD ["/run/secrets/"]