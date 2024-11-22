import os
import json
from flask import Flask, request, jsonify, Response
import aiohttp
import openai

app = Flask(__name__)


openai.api_key = os.getenv("OPENAI_API_KEY", "")
API_URL = os.getenv("API_URL", "")
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "")


def get_user_id_function_schema():
    return [
        {
            "name": "get_user_id",
            "description": "Extract user ID from the user's message data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID."},
                    "timestamp_utc": {"type": "string", "description": "UTC timestamp."},
                    "message_body": {"type": "string", "description": "Message body."}
                },
                "required": ["user_id", "timestamp_utc", "message_body"]
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

    response = await openai.ChatCompletion.acreate(**json_data)
    if not response or "choices" not in response or not response["choices"]:
        raise ValueError("LLM response is invalid or empty.")
    return response


@app.route("/chat/completions", methods=["POST"])
async def vapi_conversation():
    try:
        request_data = request.get_json()
        if not request_data or "messages" not in request_data:
            return jsonify({"error": "Invalid request. Provide a 'messages' array."}), 400

        messages = request_data.get("messages", [])
        user_utterance = next(
            (msg["content"] for msg in reversed(messages) if msg.get("role") == "user"),
            None
        )

        if not user_utterance:
            return jsonify({"error": "No valid user message found."}), 400

      
        functions = get_user_id_function_schema()
        response = await chat_completion_request(
            messages=[{"role": "user", "content": user_utterance}],
            functions=functions,
            function_call={"name": "get_user_id"}
        )

        function_call_data = response["choices"][0]["message"]["function_call"]
        arguments = json.loads(function_call_data.get("arguments", "{}"))
        user_id = arguments.get("user_id", -1)

        if user_id == -1:
            return jsonify({"error": "User ID extraction failed."}), 400

        print(f"User ID extracted: {user_id}")

     
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}") as external_response:
                if external_response.status != 200:
                    return jsonify({"error": "Failed to fetch data from external API."}), 500
                messages_data = await external_response.json()

        user_messages = [
            {"timestamp": msg["Timestamp (UTC)"], "content": msg["Message Body"]}
            for msg in messages_data if msg["User ID"] == user_id
        ]

        if not user_messages:
            return jsonify({"message": f"No interactions found for user ID {user_id}."}), 404

        sorted_messages = sorted(user_messages, key=lambda x: x["timestamp"], reverse=True)
        formatted_messages = "\n".join(
            f"{msg['timestamp']}: {msg['content']}" for msg in sorted_messages[:10]
        )
        print(f"Formatted Messages:\n{formatted_messages}")

        assistant_reply = f"""
        Here are recent interactions for user ID {user_id}:
        {formatted_messages}

        Would you like to inquire about other interactions? Say 'thank you' or 'goodbye' to end the call.
        """

        # Streaming response back to Vapi
        def generate_stream():
            yield f'data: {json.dumps({"assistant_reply": assistant_reply})}\n\n'
            yield 'data: [DONE]\n\n'

        headers = {"Content-Type": "text/event-stream"}
        return Response(generate_stream(), headers=headers)

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
