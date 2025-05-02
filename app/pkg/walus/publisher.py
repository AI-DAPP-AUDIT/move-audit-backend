import requests

class Publish:
    def __init__(self, base_url="https://publisher.walrus-testnet.walrus.space/v1"):
        self.base_url = base_url
    
    def upload(self, file_content, epochs=5, content_type='text/markdown'):
        url = f"{self.base_url}/blobs?epochs={epochs}"
        
        headers = {
            'Content-Type': content_type
        }
        
        response = requests.request("PUT", url, headers=headers, data=file_content)
        return response