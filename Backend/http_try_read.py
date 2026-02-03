import requests, time
db = "https://embedded-zenith-default-rtdb.firebaseio.com/"
path = "timeseries.json" #This node was created in the Firebase console in step 1
query = "?orderBy=\"rnd\"&startAt=0.5&endAt=1.0"
response = requests.get(db+path+query)

if response.ok:
    print(response.json())
else:
    raise ConnectionError("Could not access database: {}".format(response.text))