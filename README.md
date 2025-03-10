# Orthanc PACS with SLIM viewer

This repository combines 
- [Orthanc PACS](https://orthanc.uclouvain.be/)
- [SLIM Viewer](https://github.com/ImagingDataCommons/slim)
using DICOM web service as communication interface. 

## Quick Start

Simply execute the ``docker-compose.yml``:
```
docker compose build
docker compose run -d
```
``-d`` runs the services in *detached* mode in background. 

## Database

A DICOM database is attached as docker volume in ``docker-compose.yml``

## Update SLIM

If a new version of the viewer is published, most of the folder can be changed with the new files. 
However, for building a docker image, the Nginx configuration establishing the connection between Orthanc and Slim also has to be stored in the viewer directory: ``slim/nginx.config`` and has to be pursued. 