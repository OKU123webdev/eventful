from flask import Flask, render_template

app = Flask(__name__)

# Homepage/Index
@app.route('/')
def homepage():
    return render_template('index.html')

# Registration
@app.route('/register')
def register():
    return render_template('registration.html')

if __name__ == "__main__":
    app.run(debug=True)