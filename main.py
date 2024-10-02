
from flask import Flask, render_template, request, jsonify
import asyncio
import data_extraction
import datetime

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

@app.route('/extract', methods=['POST'])
async def extract():
    data = request.json
    media = data['media']
    start_date = data['startDate']
    end_date = data['endDate']
    try:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'message': 'Invalid date format'}), 400
    
    success = await data_extraction.run(media, start_date, end_date)
    if success:
        return jsonify({'message': 'Data extraction successful!'})
    else:
        return jsonify({'message': 'Data extraction failed!'}), 500

# @app.route("/")
# def home():
#     return render_template("index.html")



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    # asyncio.run(run())