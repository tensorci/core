import os
from src import app, socket


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 80))
  socket.run(app, host='0.0.0.0', port=port, debug=True)