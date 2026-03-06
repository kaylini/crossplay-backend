import os
import base64
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
# Allows Hostinger to talk to Render
CORS(app) 

# This grabs your secret key securely from Render
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/solve', methods=['POST'])
def solve_board():
    if 'board_image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    image = request.files['board_image']
    rack_letters = request.form.get('rack_letters', '')

    # Convert the image into a base64 string so OpenAI can "see" it
    base64_image = base64.b64encode(image.read()).decode('utf-8')

   # The Accuracy-First "Semantic Anchoring" Prompt
    prompt_text = f"""
    You are an expert Scrabble/Crossplay solver. I value ACCURACY and VALIDITY over finding the absolute highest mathematical score.
    Here is an image of the current board.
    My rack is: {rack_letters} (A '?' is a blank tile, worth 0 pts).

    CRITICAL INSTRUCTION: Do NOT use Row/Column coordinates. You are analyzing an image and will miscount the grid. 

    Instead, you must use "Word Anchoring" by following these exact steps:
    1. READ THE BOARD: Identify the existing words clearly spelled out on the board (e.g., if you see AXITE, WOBBLER, QUIZ, DEVS, DINGS, note them).
    2. FIND AN ANCHOR: Pick exactly ONE letter from one of those existing words that has plenty of empty space around it.
    3. BUILD: Form a valid English word using tiles from my rack plus that ONE anchor letter.
    4. COLLISION CHECK: Ensure your new word extends into empty space and does not accidentally lay tiles on top of other existing words.
    5. SCORE: Provide a conservative base score (A:1, B:3, C:3, D:2, E:1, F:4, G:2, H:4, I:1, J:8, K:5, L:1, M:3, N:1, O:1, P:3, Q:10, R:1, S:1, T:1, U:1, V:5, W:5, X:8, Y:5, Z:10). If you happen to see a premium square under the new tiles, include it, but do not guess if you aren't sure.

    Return ONLY the top 3 safest, most accurate moves as valid JSON. Provide the position exactly like the example:
    {{
        "moves": [
            {{"word": "PINT", "score": 14, "position": "Vertical - Connecting to the 'I' in the existing word 'QUIZ'."}},
            {{"word": "HINT", "score": 12, "position": "Horizontal - Hooking onto the end of the existing word 'DEVS' to make 'DEVSH' (if valid) or crossing an open letter."}}
        ]
    }}
    """

    try:
        # Send the image and instructions to GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=500
        )
        
        # Clean up the AI's response to ensure it is strict JSON
        result_text = response.choices[0].message.content
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        # Send the calculated moves back to Hostinger
        ai_data = json.loads(result_text)
        return jsonify(ai_data)
        
    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": "Failed to analyze board. The AI might be busy or there is an API error."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
