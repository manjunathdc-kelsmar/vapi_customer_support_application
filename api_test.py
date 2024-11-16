import requests


API_URL = 'https://vapi-demo.blame.cc'

def fetch_user_data(user_id):
    try:
        response = requests.get(f"{API_URL}")
        
        if response.status_code == 200:
            data = response.json()
            filtered_messages = []

            for obj in data:
                if obj["User ID"] == int(user_id):
                    filtered_messages.append(obj)
            print(filtered_messages)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    user_id = input("Enter User ID: ")
    fetch_user_data(user_id)
