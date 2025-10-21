from flask import Flask, render_template

app = Flask(__name__)


@app.route('/')
def index():
    """Render the home page (index.html)."""
    return render_template('index.html')


@app.route('/about')
def about():
    """Render the about page (about.html)."""
    return render_template('about.html')


@app.route('/favorites')
def favorites():
    """Render the favorites page (favorites.html)."""
    return render_template('favorites.html')


if __name__ == '__main__':
    # Run in debug mode for development. Change host/port for production.
    app.run(debug=True)
