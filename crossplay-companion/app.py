from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# This is crucial: it allows your Hostinger website to talk to this server
CORS(app) 

@app.route('/solve', methods=['POST'])
def solve_board():
    if 'board_image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    image = request.files['board_image']
    rack_letters = request.form.get('rack_letters', '')

    # Dummy data to test the connection to Hostinger
    mock_results = [
        {
            "word": "WAVY",
            "score": 45,
            "position": "Row 8, Col 4 (Horizontal) - Connects with 'Y'."
        },
        {
            "word": "VERY",
            "score": 32,
            "position": "Row 2, Col 12 (Vertical) - Forms 'AT'."
        }
    ]

    return jsonify({"moves": mock_results})

if __name__ == '__main__':
    app.run(debug=True, port=5000)