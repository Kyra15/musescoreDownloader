from flask import Flask, render_template, request, send_file
from dotenv import load_dotenv
import os
from scraper import scrape_musescore, convert_with_playwright
import shutil
import asyncio

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
        
        if os.path.exists("pages"):
            shutil.rmtree("pages")
        os.makedirs("pages")
        asyncio.run(scrape_musescore(ms_link))
        convert_with_playwright()


    return send_file(
            "static/output_score.pdf", 
            as_attachment=True, 
            download_name="ouput_score.pdf"
        )


if __name__ == '__main__':
    app.run(port=4200, debug=True)