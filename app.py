from flask import Flask, request
import requests
import time

app = Flask(__name__)


API_URL = 'https://vapi-demo.blame.cc'

@app.route('/greet', methods=['POST'])
def greet_user():
    
    message = "Hello! What user ID's last interactions do you want to know?"
    return message

@app.route('/get_interactions', methods=['POST'])
def get_interactions():

    user_id = request.json.get('user_id')

    if not user_id:
        return "Please provide a valid user ID."

    try:
        delay_message = "Please wait for 2 seconds; I'm checking for your information."
        print(delay_message)  
        time.sleep(2)  
        
        
        response = requests.get(API_URL)
        if response.status_code != 200:
            return "There was an issue fetching your information. Please try again later."

        
        data = response.json()
        interactions = [obj for obj in data if obj["User ID"] == int(user_id)]

        if not interactions:
            return "No interactions found for the specified user ID."

        
        sorted_interactions = sorted(interactions, key=lambda x: x["date"], reverse=True)

        
        most_recent = sorted_interactions[0]
        recent_message = f"The most recent interaction was on {most_recent['date']}: {most_recent['message']}."

        
        all_messages = "\n".join([f"{msg['date']}: {msg['message']}" for msg in sorted_interactions])

        
        response_message = (
            f"{recent_message}\n"
            "Would you like to hear more interactions?\n\n"
            f"Here are all the messages:\n{all_messages}"
        )

        return response_message

    except requests.exceptions.RequestException as e:
        return f"An error occurred while fetching data: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

if __name__ == '__main__':
    app.run(port=5000)
