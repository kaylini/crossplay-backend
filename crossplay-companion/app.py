import os
import base64
import json
import urllib.request
from collections import Counter
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

TILE_VALUES = {
    'A':1, 'B':3, 'C':3, 'D':2, 'E':1, 'F':4, 'G':2, 'H':4, 'I':1, 'J':8, 
    'K':5, 'L':1, 'M':3, 'N':1, 'O':1, 'P':3, 'Q':10, 'R':1, 'S':1, 'T':1, 
    'U':1, 'V':5, 'W':5, 'X':8, 'Y':5, 'Z':10
}

print("Downloading SOWPODS dictionary...")
url = "https://raw.githubusercontent.com/jesstess/Scrabble/master/scrabble/sowpods.txt"
response = urllib.request.urlopen(url)
VALID_WORDS = [word.decode('utf-8').strip().upper() for word in response.readlines()]
print(f"Loaded {len(VALID_WORDS)} words.")

def get_grid_from_ai(base64_image):
    prompt = """
    You are an Optical Character Recognition bot. Read this 15x15 Scrabble board.
    Return ONLY a raw JSON array of 15 arrays, each containing 15 strings. 
    Use uppercase letters for existing tiles, and an empty string "" for blank squares.
    Do not add any markdown, code blocks, or conversational text.
    Example format: [["", "", "T", ""...], [...], ...]
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        max_tokens=1000,
        temperature=0.0
    )
    result_text = response.choices[0].message.content.replace('```json', '').replace('```', '').strip()
    return json.loads(result_text)

def find_best_plays(grid, rack):
    rack_letters = rack.replace('?', '')
    num_blanks = rack.count('?')
    
    # 1. Gather all letters on the board to figure out what is physically possible
    board_letters = ""
    for row in grid:
        for char in row:
            if char != "":
                board_letters += char
                
    # 2. THE MASSIVE SPEED UPGRADE: Pre-filter the dictionary
    pool_counts = Counter(rack_letters + board_letters)
    possible_words = []
    for word in VALID_WORDS:
        word_counts = Counter(word)
        blanks_needed = sum(max(0, count - pool_counts[char]) for char, count in word_counts.items())
        if blanks_needed <= num_blanks:
            possible_words.append(word)

    valid_plays = []

    # 3. Now only check the possible words against the grid
    for direction in ["Horizontal", "Vertical"]:
        working_grid = grid if direction == "Horizontal" else [list(i) for i in zip(*grid)]
        
        for row_idx, row in enumerate(working_grid):
            for start_col in range(15):
                for word in possible_words:
                    word_len = len(word)
                    if start_col + word_len > 15:
                        continue

                    rack_temp = Counter(rack_letters)
                    blanks_temp = num_blanks
                    is_valid = True
                    uses_board_letter = False
                    tiles_placed = 0
                    score = 0
                    
                    if start_col > 0 and row[start_col - 1] != "":
                        continue
                    if start_col + word_len < 15 and row[start_col + word_len] != "":
                        continue

                    for i, char in enumerate(word):
                        board_char = row[start_col + i]
                        
                        if board_char != "":
                            if board_char != char:
                                is_valid = False
                                break
                            uses_board_letter = True
                            score += TILE_VALUES.get(char, 0)
                        else:
                            tiles_placed += 1
                            if rack_temp[char] > 0:
                                rack_temp[char] -= 1
                                score += TILE_VALUES.get(char, 0)
                            elif blanks_temp > 0:
                                blanks_temp -= 1
                            else:
                                is_valid = False
                                break
                    
                    if is_valid and uses_board_letter and tiles_placed > 0:
                        if tiles_placed == 7:
                            score += 40
                            
                        actual_row = row_idx + 1 if direction == "Horizontal" else start_col + 1
                        actual_col = start_col + 1 if direction == "Horizontal" else row_idx + 1
                        
                        valid_plays.append({
                            "word": word,
                            "score": score,
                            "position": f"Row {actual_row}, Col {actual_col} ({direction})"
                        })

    unique_plays = {play['word'] + play['position']: play for play in valid_plays}
    sorted_plays = sorted(unique_plays.values(), key=lambda x: x['score'], reverse=True)
    return sorted_plays[:10]

@app.route('/solve', methods=['POST'])
def solve_board():
    if 'board_image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    image = request.files['board_image']
    rack = request.form.get('rack_letters', '').upper()
    base64_image = base64.b64encode(image.read()).decode('utf-8')

    try:
        grid = get_grid_from_ai(base64_image)
        best_plays = find_best_plays(grid, rack)
        
        if not best_plays:
            return jsonify({"moves": [{"word": "No valid plays found", "score": 0, "position": "Check your letters or try a clearer image."}]})
            
        return jsonify({"moves": best_plays})
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Server timeout or AI grid extraction failed."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
