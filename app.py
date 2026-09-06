from flask import Flask, render_template, request, send_file
from dotenv import load_dotenv
import os
from scraper import scrape_musescore, convert_with_playwright, saved_pages_data
import asyncio
import io

load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = Flask(__name__)

@app.route("/")
def template():
    return render_template("index.html")


@app.route('/convert', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        ms_link = request.form.get("ms_link")
        print("user searched:", ms_link)

        saved_pages_data.clear()
        
        asyncio.run(scrape_musescore(ms_link))
        pdf_bytes = asyncio.run(convert_with_playwright(saved_pages_data))

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="output_score.pdf"
        )
    return "Method not allowed", 405


if __name__ == '__main__':
    app.run(port=4200, debug=True)