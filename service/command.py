import os

import time

print('hi from py')

queue_name = os.environ.get('QUEUE_NAME')

print(queue_name)

cycle_number = 0


from fastapi import FastAPI


app = FastAPI()


@app.get("/")
def root():
    print(queue_name)
    global cycle_number
    cycle_number += 1
    print(cycle_number)
    return {"message": "Hello World"}
