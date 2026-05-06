import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, datetime

from helpers import apology, login_required

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///project.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/catalog")
@login_required
def catalog():
    catalogs = db.execute(
        "SELECT id, identificacao, data_nascimento, valor, sexo FROM animais WHERE user_id = :user_id",
        user_id=session["user_id"]
    )

    hoje = date.today()

    for catalog in catalogs:
        nascimento = datetime.strptime(catalog["data_nascimento"], "%d/%m/%Y").date()

        anos = hoje.year - nascimento.year
        meses = hoje.month - nascimento.month

        # ainda não fez aniversário esse mês
        if hoje.day < nascimento.day:
            meses -= 1

        # se meses ficou negativo
        if meses < 0:
            anos -= 1
            meses += 12

        catalog["idade"] = f"{anos} years and {meses} months"

    total = sum(catalog["valor"] for catalog in catalogs)

    return render_template("catalog.html", catalogs=catalogs, total=total)

@app.route("/history", methods=["GET","POST"])
@login_required
def history():

    cows = db.execute(
        "SELECT identificacao, id FROM animais WHERE user_id = :user_id",
        user_id=session["user_id"]
    )

    if request.method == "POST":
        cow = request.form.get("cow")
        reason = request.form.get("reason")
        cow_id = request.form.get("cow_id")

        if not cow:
            return apology("Cow is required")
        if not reason:
            return apology("Reason is required")

        db.execute(
            "INSERT INTO removals (user_id, identificacao, reason) VALUES (:user_id, :identificacao, :reason)",
            user_id=session["user_id"],
            identificacao=cow,
            reason=reason
        )

        db.execute(
            "DELETE FROM animais WHERE id = :id AND user_id = :user_id",
            id=cow_id,
            user_id=session["user_id"]
        )

        cows = db.execute(
            "SELECT identificacao, id FROM animais WHERE user_id = :user_id",
            user_id=session["user_id"]
        )

    removals = db.execute(
        "SELECT identificacao, reason, removed_at FROM removals WHERE user_id = :user_id ORDER BY removed_at DESC",
        user_id=session["user_id"]
    )

    return render_template("history.html", cows=cows, removals=removals)

#@app.route("/clear_history", methods=["POST"])
#@login_required
#def clear_history():
    #db.execute(
        #"DELETE FROM removals WHERE user_id = :user_id",
        #user_id=session["user_id"]
    #)

    #return redirect("/history")


@app.route("/new", methods=["GET", "POST"])
@login_required
def new():

    identificacao = db.execute(
        "SELECT identificacao FROM animais WHERE user_id = :user_id",
        user_id=session["user_id"]
    )

    if request.method == "POST":
        animal = request.form.get("animal")
        birth = request.form.get("birth")
        price = request.form.get("price")
        sex = request.form.get("sex")

        ja_existe = db.execute(
            "SELECT identificacao FROM animais WHERE user_id = :user_id AND identificacao = :animal",
            user_id=session["user_id"],
            animal=animal
        )

        if ja_existe:
            return apology("Already exists")
        if not birth:
            return apology("Birthday is required")
        if not sex:
            return apology("Sex is required")
        if not animal:
            return apology("Animal identification is required")
        elif not price or not price.isdigit() or int(price) <= 0:
            return apology("Must be a positive number for price")

        db.execute(
            "INSERT INTO animais (user_id, identificacao, data_nascimento, valor, sexo) VALUES (:user_id, :animal, :birth, :price, :sex)",
            user_id=session["user_id"],
            animal=animal,
            birth=birth,
            price=price,
            sex=sex
        )

    insert_time = db.execute(
            "SELECT criado_em, identificacao FROM animais WHERE user_id = :user_id ORDER BY criado_em DESC",
            user_id=session["user_id"]
        )

    return render_template("new.html", insert_time=insert_time )

@app.route("/control", methods=["GET", "POST"])
@login_required
def control():

    total_animals = db.execute(
        "SELECT identificacao, sexo FROM animais WHERE user_id = :user_id",
        user_id=session["user_id"]
    )

    total = 0
    for animals in total_animals:
        if animals:
            total+=1

    total_females = 0

    for animal in total_animals:
        if animal["sexo"] == "Female":
            total_females = total_females + 1

    total_males = 0

    for animal in total_animals:
        if animal["sexo"] == "Male":
            total_males = total_males + 1

    return render_template("control.html", total=total, total_females=total_females, total_males=total_males)


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # clear previous session
    session.clear()

    if request.method == "POST":
        # credentials
        if not request.form.get("username"):
            return apology("Username is required", 400)
        elif not request.form.get("password"):
            return apology("Password is required", 400)
        elif not request.form.get("confirmation"):
            return apology("You must confirm your password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords do not match", 400)

        # search database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # checking for duplicates
        if len(rows) != 0:
            return apology("Username already exists", 400)

        # register new valid user
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get(
            "username"), generate_password_hash(request.form.get("password")))

        # search for the newly registered user
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # create a new session for the user
        session["user_id"] = rows[0]["id"]

        # back to home
        return redirect("/")
    else:
        return render_template("register.html")

#if __name__ == "__main__":
    #app.run(debug=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)