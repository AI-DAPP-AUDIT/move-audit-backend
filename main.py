import os
from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from app.models.order import db, Order, OrderStatus
from app.api.order import OrderResource
from app.api.audit import AuditResource
from app.pkg.sui.sui import SuiClient
import tomllib
from app.pkg.agents.manager import ClientManager
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
api = Api(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logger = app.logger
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(
    os.path.join(log_dir, 'app.log'),
    maxBytes=10*1024*1024,
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))

logger.addHandler(file_handler)
logger.addHandler(console_handler)


config_file = os.path.join(BASE_DIR, "config/config.toml" if os.getenv("PROD") else "config/config.test.toml")
logger.info("Loading config file: %s", config_file)


with open(config_file, 'rb') as f:
    config = tomllib.load(f)
    app.config.update(config)

logger.info("Config loaded successfully:", app.config)


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
client_manager = ClientManager(app.config['openai']['model'], app.config['openai']['api_key'], app)

def init_db():
    with app.app_context():
        db.create_all()
        print("database create success！")

api.add_resource(OrderResource, '/api/orders', resource_class_kwargs={'sui_client': sui_client})
api.add_resource(AuditResource, '/api/audits', resource_class_kwargs={'sui_client': sui_client, 'client_manager': client_manager})



@app.route('/')
def hello_world():
    return 'Hello, World!'

def main():
    init_db()
    client_manager.run()
    app.run(debug=True, host='0.0.0.0', port=5000)
    

if __name__ == "__main__":
    main()
