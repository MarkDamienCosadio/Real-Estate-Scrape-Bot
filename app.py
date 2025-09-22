from flask import Flask, render_template, request
import pandas as pd
import os

app = Flask(__name__)

CSV_FILE = 'main_listing.csv'

def get_listings():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        return df.to_dict(orient='records')
    return []

@app.route('/')
def index():
    listings = get_listings()
    return render_template('dashboard.html', listings=listings)

if __name__ == '__main__':
    app.run(debug=True)
