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

    # The exact instructions for the AI
    prompt_text = f"""
    You are an expert at the game NYT Crossplay. 
    Here is an image of the current board. 
    My current rack is: {rack_letters} 
    (A '?' in the rack represents a blank tile that can act as any letter but scores 0 points).
    
    The tile point values are: 
    A:1, B:3, C:3, D:2, E:1, F:4, G:2, H:4, I:1, J:8, K:5, L:1, M:3, N:1, O:1, P:3, Q:10, R:1, S:1, T:1, U:1, V:5, W:5, X:8, Y:5, Z:10.
    
    Analyze the board visually. Find the top 3 highest-scoring valid moves I can play right now by connecting my rack letters to the existing letters on the board.
    
    Return ONLY valid JSON in this exact format. Do not include markdown formatting, code blocks, or conversational text:
    {{
        "moves": [
            {{"word": "EXAMPLE", "score": 40, "position": "Row 5, Col 3 (Horizontal) - Connects with the 'E' in 'TEAM'."}}
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
        return jsonify({"error": "Failed to analyze board. The AI might be busy."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
