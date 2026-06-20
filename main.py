from flask import Flask
from routes.auth import auth_bp
import secrets

app = Flask(__name__)
app.register_blueprint(auth_bp)
app.secret_key = secrets.token_hex(16)

if __name__ == "__main__":
    app.run(debug=True)
