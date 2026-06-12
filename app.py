from flask import Flask, render_template, request, redirect, session
from auth import validate_login
from datetime import datetime
import database




def get_todayDate():
    time = datetime.now()
    date = time.strftime("%m/%d/%Y")

    return date


app = Flask(__name__)
app.secret_key = "secret-key"

database.initialize_database() #Creates the database right when the app starts
    

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if validate_login(username, password):
            user = database.search_user_by_name(username)
            
            session['user_id'] = user['id']
            session["username"] = user["name"]
            session["role"] = user["role"]
            
            return redirect("/dashboard")
        else:
            return render_template("index.html", error="Invalid Credentials")
        
    return render_template("index.html")

@app.route("/test")
def test():
    return f"""
    User: {session.get('username')}<br>
    Role: {session.get('role')}
    """


@app.route('/admin', methods=["GET", "POST"])
def admin():
    error = None
    success = None

    user_count = database.get_user_count()

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        if not username or not password:
            error = "Both fields are required"
        else:
            database.create_user(username, password, role)
            success = "User created successfully"

    all_users = database.search_all_users()
    return render_template("admin.html", all_users=all_users, error=error, success=success, user_count=user_count)

@app.route('/dashboard')
def dashboard():
    date = get_todayDate()

    total_herd = database.get_animal_count()

    status_summary = database.get_status_summary()

    attention_animals = database.get_attention_animals()

    missing_health_updates = 2
    recent_alerts = 1
    return render_template("dashboard.html",
                           date=date,

                           total_herd=total_herd,

                           attention_animals=attention_animals["attention"],
                           critical_animals=attention_animals["critical"],

                           attention_count=status_summary["attention"],
                           critical_count=status_summary["critical"],


                           missing_health_updates=missing_health_updates,
                           recent_alerts=recent_alerts,
                           )

@app.route("/register", methods=["GET","POST"])
def register():
    date = get_todayDate()
    if request.method == "POST":
        arrival_day = database.get_time()
        tag = request.form.get("input_tag")
        race = request.form.get("input_race")
        sex = request.form.get("input_sex")
        birth_day = request.form.get("input_birthday")
        weight = request.form.get("input_weight")

        print(f"DEBUG -> Tag: {tag}, Race: {race}, Weight: {weight} ")
        database.new_animal(tag, arrival_day, race, sex, birth_day, weight)
        return redirect("/animals")
    
    return render_template("register.html", date=date)

@app.route("/animals")
def animals():
    date = get_todayDate()
    animal_data = database.search_all()
    status_filter = request.args.get("status")

    return render_template(
        "animals.html",
        animal_list=animal_data,
        date=date
    )


@app.route("/delete", methods=["POST"])
def delete():
    delete_id = request.form.get("animal_id")
    if delete_id:
        database.delete_animal(int(delete_id)) # SQLite can't receive an string. To make sure I convert everytime here.
    return redirect("/animals")

@app.route("/edit", methods=["GET","POST"])
def edit():
    if request.method == "POST":
        cattle_id = request.form.get("animal_id")
        new_weight = request.form.get("weight")
        if cattle_id and new_weight:
            new_weight = float(new_weight)
            database.add_weight(int(cattle_id), new_weight)
    return redirect("/animals")

if __name__ == "__main__":
    app.run(debug=True)