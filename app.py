import flask
from flask import Flask

app = Flask(__name__)

# Главная страница
@app.route("/")
def home():
    return "<h1>Главная страница</h1><p>Добро пожаловать!</p>"

# Страница "О нас"
@app.route("/about")
def about():
    return "<h1>О нас</h1><p>Мы изучаем Flask!</p>"

# Страница "Контакты"
@app.route("/contact")
def contact():
    return "<h1>Контакты</h1><p>Свяжитесь с нами: email@example.com</p>"

if __name__ == "__main__":
    app.run(debug=True)