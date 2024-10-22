celery -A worker worker --loglevel=info

uvicorn main:app --reload
http://localhost:8000/compile/


curl -X GET "http://localhost:8000/status/{1ef6549f-57a6-4213-989a-acc761d47cfd}"
curl -X GET "http://localhost:8000/status/87ee4039-86a2-4a4b-8ecd-1cbe5545fd75"
