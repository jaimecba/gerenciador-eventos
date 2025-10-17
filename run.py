# run.py
from wsgi import create_app # <--- LINHA ALTERADA!

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)