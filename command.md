python -m venv evn
evn\Scripts\activate
pip install -r requirements.txt

docker exec -it django_app bash

gcloud run deploy thesis-web --source . --region us-central1 --allow-unauthenticated --add-cloudsql-instances aerial-yeti-480303-f5:us-central1:thesis-db
