import os
from flask import Flask, request, jsonify
import aiohttp
import openai

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY", "")
API_URL = os.getenv("API_URL", "https://vapi-demo.blame.cc")

def get_user_id_function_schema():
    return [
        {
            "name": "get_user_id",
            "description": "Extract user ID from the user's message data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The ID of the user extracted from the message data."
                    },
                    "timestamp_utc": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The timestamp in UTC when the message was sent."
                    },
                    "message_body": {
                        "type": "string",
                        "description": "The content of the message sent by the user."
                    }
                },
                "required": ["user_id", "timestamp_utc", "message_body"],  
            }
        }
    ]


async def chat_completion_request(messages, functions=None, function_call=None):
    json_data = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
    }
    if functions:
        json_data["functions"] = functions
    if function_call:
        json_data["function_call"] = function_call

    #print("ChatCompletion Request Payload:", json_data)  
    response = await openai.ChatCompletion.acreate(**json_data)
    #print("ChatCompletion Response:", response)  
    return response

@app.route('/test-async')
async def test_async():
    return {'message': 'Async is working!'}

@app.route("/chat/completions", methods=["POST"])
async def vapi_conversation():
    try:
        
        request_data = request.get_json()
        #print("Incoming Request Data:", request_data) 

        if not request_data or "messages" not in request_data:
            #print("Error: Invalid request. Missing 'messages'. Request data:", request_data)
            return jsonify({"error": "Invalid request. Please provide a 'messages' array."}), 400

        
        messages = request_data.get("messages", [])
        if not isinstance(messages, list) or len(messages) == 0:
           # print("Error: 'messages' is empty or invalid. Value:", messages)
            return jsonify({"error": "Invalid messages array. Please provide valid messages."}), 400

        
        user_utterance = None
        for message in reversed(messages):
            if message.get("role") == "user" and "content" in message:
                user_utterance = message["content"]
                break

        if not user_utterance or not user_utterance.strip():
            #print("Error: No valid user utterance found in messages. Messages:", messages)
            return jsonify({"error": "No valid user utterance found."}), 400

     
        messages = [{"role": "user", "content": user_utterance}]
        functions = get_user_id_function_schema()

        #print("Messages Payload for Function Call:", messages)  
        #print("Function Schema:", functions)  

        response = await chat_completion_request(
            messages=messages,
            functions=functions,
            function_call={"name": "get_user_id"}
        )

        if "choices" not in response or not response["choices"]:
            print("Error: Invalid OpenAI response. Response:", response)
            return jsonify({"error": "Could not extract user ID."}), 400

        function_call_data = response["choices"][0]["message"]["function_call"]
        #print("Function Call Data:", function_call_data)  

        arguments = function_call_data.get("arguments", {})
        user_id = int(arguments.get("user_id", -1))
        print("Extracted User ID:", user_id)  

        if user_id == -1:
            return jsonify({"error": "User ID extraction failed."}), 400

     
        print("Fetching data from API URL:", API_URL)  
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}") as external_response:
                print("External API Response Status:", external_response.status)  
                response_text = await external_response.text()
                print("External API Response Text:", response_text)  
                if external_response.status != 200:
                    return jsonify({"error": "Failed to fetch data from the external API."}), 500
                messages = await external_response.json()

        print("External API Messages:", messages) 

        user_messages = [
            {
                "timestamp": msg["Timestamp (UTC)"],
                "content": msg["Message Body"],
            }
            for msg in messages
            if msg["User ID"] == user_id
        ]

        if not user_messages:
            #print("No interactions found for user ID:", user_id)  
            return jsonify({"message": f"No interactions found for user ID {user_id}."}), 404

        
        sorted_messages = sorted(user_messages, key=lambda x: x["timestamp"], reverse=True)
        #print("Sorted Messages:", sorted_messages)  # 

        latest_message = sorted_messages[0]
        formatted_messages = "\n".join(
            [f"{msg['timestamp']}: {msg['content']}" for msg in sorted_messages]
        )
        prompt = f"""
        The user has asked about their interactions. 
        Here are the messages for user ID {user_id}, from most recent to oldest:
        {formatted_messages}.
        
        The most recent interaction was on {latest_message['timestamp']}. 
        Now, ask the user if they would like to know about any other interactions.
        """
        print("AI Prompt:", prompt)  

        ai_response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        assistant_reply = ai_response["choices"][0]["message"]["content"]
        print("Assistant Reply:", assistant_reply)  

        return jsonify({
            "fetch_message": "Please wait while we fetch your information.",
            "assistant_reply": assistant_reply,
        })

    except Exception as e:
        print("Error:", str(e))  
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
