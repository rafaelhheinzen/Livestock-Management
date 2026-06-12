import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

### TIME SETUP
def get_time():
    time = datetime.now()
    date = time.strftime("%m/%d/%Y")

    return date

### DATABASE SETUP
def database_connect():
    conn = sqlite3.connect("data.db", timeout=10) #Connects to the database file
    conn.row_factory = sqlite3.Row #Allows access the rows by the name (e.g: line["name"]) instead of the index (e.g: line[0])
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def initialize_database():
    conn = database_connect()

    #USERS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT UNIQUE,
                 password TEXT,
                 role TEXT DEFAULT 'worker'
                 )
    """)


    #ANIMAL TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cattle (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- ID of the animal,
            arrival_day DATE, -- day which the animal came to the ranch
            tag TEXT UNIQUE, -- physical identification of the animal
            race TEXT, -- Race, ex: Angus, Nelore
            sex TEXT CHECK(sex IN('M', 'F')), -- Only M(for males) or F(for females)
            birth_day DATE,
            status TEXT DEFAULT 'Active' -- Active, Sold or Dead
            )
                 
                 
        """)
    
    #WEIGHT TABLE
    conn.execute("""
            CREATE TABLE IF NOT EXISTS weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cattle_id INTEGER NOT NULL,
            weight REAL,
            weigh_day DATE NOT NULL,

            FOREIGN KEY (cattle_id) -- Connection with the cattle table
            REFERENCES cattle(id) -- Look at the id column inside the cattle table
            ON DELETE CASCADE -- When delete the animal from table cattle, also deletes its weight here
            )
                 """)
    

    data = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if data == 0:

        hashed = generate_password_hash("admin123")

        conn.execute("""
            INSERT INTO users (name, password, role)
            VALUES (?, ?, ?)
        """, ("admin", hashed, "admin"))

    conn.commit()
    conn.close()


### CREATE INFO

def new_animal(tag, arrival_day, race, sex, birth_day, weight):
    conn = database_connect()
    try:
        #Insert animal
        cursor = conn.execute("""
                INSERT INTO cattle (tag, arrival_day ,race, sex, birth_day) 
                VALUES (?, ?, ?, ?, ?)
            """, (tag, arrival_day, race, sex, birth_day))
        
        #Get generated animal id
        cattle_id = cursor.lastrowid


        #Insert initial weight
        conn.execute("""
                INSERT INTO weights (cattle_id, weight, weigh_day)
                VALUES (?, ?, ?)
                """, (cattle_id, weight, get_time()))


        conn.commit()
    except Exception as e:
        print(f"Error when adding: {e}")
    finally:
         conn.close()


def delete_animal(cattle_id):
    conn = database_connect()
    try:
        conn.execute("DELETE FROM cattle WHERE id = ?", (cattle_id,))
        conn.commit()
    finally:
        conn.close()


def add_weight(cattle_id, new_weight):
    conn = database_connect()
    try:
        #Get last weight
        last = conn.execute("""
            SELECT weight
            FROM weights
            WHERE cattle_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (cattle_id,)).fetchone()

        if last:
            old_weight = last["weight"] #-> Defines the old weight
            difference = new_weight - old_weight #-> Set the difference between actual and last weight
            print(f"Difference: {difference} kg")


        #Inserting the new values into weights table
        conn.execute("""
            INSERT INTO weights (
            cattle_id,
            weight,
            weigh_day
            )
            VALUES (?, ?, ?)
        """, (
            cattle_id,
            new_weight,
            get_time()
        ))

        conn.commit()
        
    except Exception as e:
        print(f"Error when adding: {e}")
    finally:
        conn.close()

def create_user(name, password, role):
    conn = database_connect()
    try:
        hashed = generate_password_hash(password)
        conn.execute("INSERT INTO users (name, password, role) VALUES (?, ?, ?)", (name, hashed, role))
        conn.commit()
    finally:
        conn.close()




### GET INFO
def search_all():
    conn = database_connect()
    animal_data = conn.execute("""
        SELECT
            cattle.id,
            cattle.tag,
            cattle.arrival_day,
            cattle.race,
            cattle.sex,
            cattle.birth_day,
            weights.weight,
            weights.weigh_day
        FROM cattle

        LEFT JOIN weights
        ON weights.id = (
            SELECT id
            FROM weights w2
            WHERE w2.cattle_id = cattle.id
            ORDER BY w2.id DESC
            LIMIT 1
        )
    """).fetchall()
    conn.close()
    animals = []

    #Adds healthy status inside the animal without creating a new row into the database
    for animal in animal_data:

        animal_dict = dict(animal) #Turns sqlite3.Row into a normal Python dictionary

        animal_dict["health_status"] = get_animal_status(animal["id"])

        animals.append(animal_dict) #Stores the upgraded animal inside a new list.

    return animals

def search_all_users():
    conn = database_connect()
    try:
        users = conn.execute("SELECT id, name, password FROM users").fetchall()
        return users
    finally:
        conn.close()

def search_user_by_name(name):
    conn = database_connect()
    try:
        user = conn.execute("SELECT id, name, password, role FROM users WHERE name = ?", (name,)).fetchone()
        return user
    finally:
        conn.close()


def get_user_count():
    conn = database_connect()

    data = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    conn.close()

    return data

def get_animal_count():
    conn = database_connect()
    data = conn.execute("SELECT COUNT(*) FROM cattle")
    count = data.fetchone()[0]
    conn.close()

    return count    



### CATTLE ANALYSIS
def get_animal_status(cattle_id):
    conn = database_connect()

    weights = conn.execute("""
        SELECT weight, weigh_day
        FROM weights
        WHERE cattle_id = ?
        ORDER BY id DESC
        LIMIT 2
    """, (cattle_id,)).fetchall()

    conn.close()

    if len(weights) < 2:
        return "Lack of info to return status"
    
    newest = weights[0] #Select the first row (the newest weight row)
    older = weights[1] #Select the second row (the oldest weight row)

    new_weight = newest["weight"] #Select the "weight" column from the newest row
    old_weight = older["weight"] #Select the "weight" column from the oldest row

    new_date = datetime.strptime(newest["weigh_day"], "%m/%d/%Y") #Get the date from the new weight
    old_date = datetime.strptime(older["weigh_day"], "%m/%d/%Y") #Get the date from the old weight

    days = (new_date - old_date).days
    # Prevent division by zero
    if days == 0:
        days = 1

    gain_per_day = (new_weight - old_weight) / days

 


    #Based on all data, define the health status for the cattle
    if 0.5 <= gain_per_day <= 1.5:
        return "healthy"

    elif 0 <= gain_per_day < 0.5:
        return "attention"

    else:
        return "critical"

def get_status_summary():

    animals = search_all()

    summary = {
        "healthy": 0,
        "attention": 0,
        "critical": 0
    }

    for animal in animals:

        status = animal["health_status"]

        if status in summary:
            summary[status] += 1

    return summary


def get_attention_animals():
    animals = search_all()

    result = {
        "attention": [],
        "critical": []
    }

    for animal in animals:

        status = animal["health_status"]

        if status == "attention":
            result["attention"].append(animal["tag"])
        elif status == "critical":
            result["critical"].append(animal["tag"])

    return result