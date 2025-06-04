from app import app
from whitenoise import WhiteNoise

# Wrap the Flask app with WhiteNoise for static file serving
app = WhiteNoise(app, root='static/', prefix='static/')

if __name__ == "__main__":
    app.run() 