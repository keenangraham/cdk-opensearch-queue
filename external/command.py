import os

from fastapi import FastAPI

from opensearchpy import OpenSearch


OS_URL = 'https://' + os.environ.get('OPENSEARCH_URL')


app = FastAPI()


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/search")
def search():
    client = OpenSearch(
        OS_URL
    )
    return client.search(
        index='xyz',
        body={
            'query': {
                'match_all': {}
            }
        }
    )
