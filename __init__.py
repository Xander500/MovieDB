from flask import Flask
dbtour_app = Flask(__name__)
from dbtourprod import routes
