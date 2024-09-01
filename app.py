from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import matplotlib.pyplot as plt
import io
import base64
from werkzeug.security import generate_password_hash, check_password_hash

# Flask app setup
app = Flask(__name__)
app.secret_key = ''  # Replace with your secret key

# LoginManager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS expenses
                 (id INTEGER PRIMARY KEY, amount REAL, category TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
    conn.commit()
    conn.close()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        data = c.fetchone()
        conn.close()
        if data:
            return User(data[0], data[1], data[2])
        return None

    @staticmethod
    def find_by_username(username):
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        data = c.fetchone()
        conn.close()
        if data:
            return User(data[0], data[1], data[2])
        return None

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Route for index page with expenses visualization
@app.route('/')
@login_required
def index():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute("SELECT amount, category FROM expenses")
    data = c.fetchall()
    conn.close()

    # Prepare data for visualization
    categories = [row[1] for row in data]
    amounts = [row[0] for row in data]

    # Create bar chart
    plt.figure(figsize=(10, 5))
    plt.bar(categories, amounts, color='blue')
    plt.xlabel('Category')
    plt.ylabel('Amount')
    plt.title('Expenses by Category')

    # Save plot to a bytes object
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()  # Close the plot to free up memory

    return render_template('index.html', plot_url=plot_url)

# Route to add expenses
@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense():
    amount = request.form['amount']
    category = request.form['category']
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute("INSERT INTO expenses (amount, category) VALUES (?, ?)", (amount, category))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose a different username.', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.find_by_username(username)
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

# Route for user logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
