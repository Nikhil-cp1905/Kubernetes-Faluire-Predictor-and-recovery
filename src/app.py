from flask import Flask
from flask_socketio import SocketIO
from threading import Thread
import predictgemini

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

#exposing socket
predictgemini.socketio = socketio

@app.route("/")
def index():
    return "K8s Monitoring Dashboard Backend Running"

if __name__ == "__main__":
    Thread(target=predictgemini.main).start()
    socketio.run(app, host="0.0.0.0", port=5000)

