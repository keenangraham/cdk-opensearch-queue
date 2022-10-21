import os

import time

print('hi from py')

queue_name = os.environ.get('QUEUE_NAME')

print(queue_name)

cycle_number = 0

while True:
    print('running some cycle', cycle_number)
    cycle_number += 1
    time.sleep(60)
