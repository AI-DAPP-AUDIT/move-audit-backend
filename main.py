import os
from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from app.models.order import db, Order, OrderStatus
from app.api.order import OrderResource
from app.api.audit import AuditResource
from app.pkg.sui import SuiClient
import tomllib

app = Flask(__name__)
api = Api(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


config_file = os.path.join(BASE_DIR, "config/config.toml" if os.getenv("PROD") else "config/config.test.toml")
print("Loading config file: ", config_file)


with open(config_file, 'rb') as f:
    config = tomllib.load(f)
    app.config.update(config)

print("Config loaded successfully:", app.config)


CORS(app, resources={
    r"/api/*": {
        "origins": app.config['cors']['origins'],
        "methods": app.config['cors']['methods'],
        "allow_headers": app.config['cors']['allow_headers'],
        "supports_credentials": app.config['cors']['supports_credentials'],
        "max_age": app.config['cors']['max_age']
    }
})

DATABASE_PATH = os.path.join(BASE_DIR, app.config['database']['path'])
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

SUI_URL = app.config['sui']['url']
sui_client = SuiClient(url=SUI_URL)


os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

db.init_app(app)

def init_db():
    with app.app_context():
        db.create_all()
        print("database create success！")

api.add_resource(OrderResource, '/api/orders', resource_class_kwargs={'sui_client': sui_client})
api.add_resource(AuditResource, '/api/audits', resource_class_kwargs={'sui_client': sui_client})

@app.route('/')
def hello_world():
    return 'Hello, World!'

def main():
    init_db()
    app.run(debug=True)

if __name__ == "__main__":
    main()
