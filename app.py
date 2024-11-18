import os
import asyncio
from flask import Flask, request, jsonify
import aiohttp
import openai


app = Flask(__name__)


openai.api_key = os.getenv("OPENAI_API_KEY", "your_openai_key")
API_URL = os.getenv("API_URL", "https://vapi-demo.blame.cc")


@app.route("/vapi/conversation", methods=["POST"])
async def vapi_conversation():
    try:
        
        request_data = request.get_json()
        if not request_data or "user_id" not in request_data:
            return jsonify({"error": "Invalid request. Please provide a user_id."}), 400

        
        try:
            user_id = int(request_data["user_id"])
        except ValueError:
            return jsonify({"error": "Invalid user_id. It must be an integer."}), 400

        
        fetch_message = "Please wait while we fetch your information."

        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}") as response:
                if response.status != 200:
                    return jsonify({"error": "Failed to fetch data from the external API."}), 500
                messages = await response.json()

        
        user_messages = [
            {
                "timestamp": msg["Timestamp (UTC)"],
                "content": msg["Message Body"]
            }
            for msg in messages if msg["User ID"] == user_id
        ]

        if not user_messages:
            return jsonify({"message": f"No interactions found for user ID {user_id}."}), 404

       
        sorted_messages = sorted(user_messages, key=lambda x: x["timestamp"], reverse=True)

        
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

        
        ai_response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        assistant_reply = ai_response["choices"][0]["message"]["content"]

        
        return jsonify({
            "fetch_message": fetch_message,
            "assistant_reply": assistant_reply
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
