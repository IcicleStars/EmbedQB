# dashboard.py is the entry point for the web dashboard \
# and initializes the app, registers the sensors, and ML Blueprints
import os

os.environ["MPLBACKEND"] = "Agg"

from flask import Flask, render_template

import analysis
from api.ml_routes import ml_bp
from api.sensor_routes import sensor_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "../templates")
STATIC_DIR = os.path.join(BASE_DIR, "../static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.register_blueprint(sensor_bp)
app.register_blueprint(ml_bp)


@app.route("/")
def index():
    return render_template("index.html", threshold=analysis.THRESHHOLD_VAL)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, threaded=True)