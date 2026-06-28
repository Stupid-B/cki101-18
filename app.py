from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "我是功能一"

if __name__ == '__main__':
    # Running on 0.0.0.0 is required for Docker containers to be accessible externally
    app.run(host='0.0.0.0', port=5000)
