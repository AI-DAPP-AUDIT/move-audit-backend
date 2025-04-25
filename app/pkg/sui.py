import requests
import json

class SuiClient:
    def __init__(self, url: str):
        self.url = url

        
    def query(self, digest: str):
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sui_getEvents",
            "params": [
                digest
            ]
        })
        headers = {
            'Content-Type': 'application/json'
        }
       
        response = requests.request("POST", self.url, headers=headers, data=payload)
        if response.status_code == 200:
            print(response.text)
            parsed_response = json.loads(response.text)
            return parsed_response
        else:
            print(f"Transaction query failed: {response.status_code}")
            raise Exception(f"Transaction query failed: {response.status_code}")
    
