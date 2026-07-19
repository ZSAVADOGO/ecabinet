import requests
import json

api_key = "uk_Y0HfsCT8lVSMusjdDqas_GnTSiS2aXdjDAcaMVKoAZtCK-HTm--OVx-jSVAsOP3q"

url = 'https://api.httpsms.com/v1/messages/send'

headers = {
    'x-api-key': api_key,
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

payload = {
    "content": "Salut ces comment",
    "from": "+22670250633",
    "to": "+22679549337"
}

response = requests.post(url, headers=headers, data=json.dumps(payload))

print(response.json())