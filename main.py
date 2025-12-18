from flask import Flask, render_template, request, redirect, url_for

# Initialize the Flask application
app = Flask(__name__)

# In-memory database (a simple list of dictionaries)
submissions = []

# Load existing submissions from the file on startup
try:
    with open("submissions.txt", "r") as f:
        for line in f:
            name, email = line.strip().split(",", 1)
            submissions.append({'name': name, 'email': email})
except FileNotFoundError:
    # If the file doesn't exist yet, start with an empty list
    pass

@app.route('/')
def index():
    """
    Renders the main page with the submission form.
    """
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    """
    Handles the form submission.
    Stores the name and email in the in-memory database and updates the file.
    """
    name = request.form.get('name')
    email = request.form.get('email')
    if name and email:
        # Add to in-memory list
        submissions.append({'name': name, 'email': email})
        # Append to the submissions.txt file
        with open("submissions.txt", "a") as f:
            f.write(f"{name},{email}\n")
    return redirect(url_for('entries'))

@app.route('/entries')
def entries():
    """
    Displays all submitted entries in a table.
    """
    return render_template('entries.html', entries=submissions)

if __name__ == '__main__':
    # To run this application:
    # 1. Make sure you have Flask installed: pip install Flask
    # 2. Run this script: python main.py
    # 3. Open your web browser and go to: http://127.0.0.1:5000
    app.run(debug=True)