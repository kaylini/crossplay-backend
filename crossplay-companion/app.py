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

   # The ultimate, algorithm-mimicking prompt
    prompt_text = f"""
    You are a strict, mathematical Scrabble engine analyzing a NYT Crossplay board.
    My rack is: {rack_letters} (A '?' is a blank tile, worth 0 pts).
    
    You MUST execute this algorithm in your mind before outputting the final JSON:

    PHASE 1: RIGID GRID MAPPING
    - The board is a 15x15 grid. Row 1 is the top, Col 1 is the far left.
    - Scan the board and map the exact Row and Column of EVERY existing letter. 
    - Treat these existing letters as solid brick walls. You absolutely CANNOT place a new letter on these coordinates.

    PHASE 2: COLLISION-FREE PATHFINDING
    - Find the open, completely empty squares adjacent to the existing letters.
    - Form a valid English word using my rack tiles + at least one existing board letter.
    - STRICT CHECK: Verify coordinate-by-coordinate that every single new tile you are placing lands on an EMPTY square. If a tile lands on an existing letter, the move is invalid. Discard it.

    PHASE 3: SCORING
    - A:1, B:3, C:3, D:2, E:1, F:4, G:2, H:4, I:1, J:8, K:5, L:1, M:3, N:1, O:1, P:3, Q:10, R:1, S:1, T:1, U:1, V:5, W:5, X:8, Y:5, Z:10.
    - +40 points for using all 7 tiles. Calculate 2W/3W/2L/3L accurately.

    Return ONLY the top 3 verified, collision-free moves as valid JSON. Do not output your Phase 1/2/3 thinking, ONLY the JSON:
    {{
        "moves": [
            {{"word": "EXAMPLE", "score": 40, "position": "Row 5, Col 3 (Horizontal) - Connects to the 'E' at Row 5, Col 4. Tiles placed on verified empty squares."}}
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
