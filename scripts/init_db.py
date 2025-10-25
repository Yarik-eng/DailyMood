import os
import sys

# Ensure the project root is on sys.path so `import app` works when this
# script is executed from the scripts/ directory.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app
from models import db


def init_db():
    with app.app_context():
        db.create_all()
        print('DB initialized at', app.config.get('SQLALCHEMY_DATABASE_URI'))


if __name__ == '__main__':
    init_db()
