import requests

from mediaserver.constants import USER_API_URL

def verify_token(token, api_url=USER_API_URL):
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            return True
            # return {"status": "success", "data": response.json()}
        else:
            # return {"status": "error", "message": response.json().get("detail", "Invalid token")}
            return False
    except Exception as e:
        return {"status": "error", "message": str(e)}