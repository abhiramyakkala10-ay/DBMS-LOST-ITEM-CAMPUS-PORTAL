import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../campus_lf'))

from app import app

@app.route('/api/health', methods=['GET'])
def health():
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    app.run()
