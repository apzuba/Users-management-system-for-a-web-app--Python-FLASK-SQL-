from flask import (
    Flask, 
    session, 
    redirect, 
    url_for, 
    escape, 
    request,
    render_template,
    g,
    jsonify)
from multiprocessing import Value
from gothonweb import planisphere
import os, sys

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

from functools import wraps


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True


db = SQLAlchemy(app)

#Class for handling the user data within the SQL database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    score = db.Column(db.Integer, default = 0)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())

    def __repr__(self):
        return f'<User {self.username}> '


#AUTH and security decorators 
def login_req(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            return redirect(url_for('login', code=302 ))
        return f(*args, **kwargs)
    return decorated_function 

def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        users = User.query.all()
        user = [x for x in users if x.id == session.get('user_id')][0]
        if user.username != "admin":
            return redirect(url_for('login', code=302 ))
        return f(*args, **kwargs)
    return decorated_function
#------------------------


new_user = []  # User status gauge for managing the feedback pop-up. 
new_user_dict = {
        1:       "Login - No such User",
        2:       "Login - Typed wrong password",
        7:       "Delete - Account has been deleted",
        8:       "Delete - Typed wrong password, less than 3 tries",
        9:       "Delete - Wrong password; Reached the tries limit",
        19:      "Register - Typed wrong password", 
        20:      "Register -  New User registered"
}
        


try_del_value = Value('i', 0)   #Counts the tries to delete an account

def del_try():                  #Counter function
    with try_del_value.get_lock():
        try_del_value.value += 1
        out = try_del_value.value
    return jsonify(count=out)

#Checks if the user is already logged in.
@app.before_request
def before_request():
    users = User.query.all()
    try:
        if 'user_id' in session:
            user = [x for x in users if x.id == session['user_id']][0]
            g.user = user
    except:
        pass

#The landing page - Login.
@app.route('/', methods=['POST', 'GET'])

def login():
    try:
        print(f"User ID: {session.get('user_id')}, Status: {new_user_dict[new_user[0]]}")
    except:
        print(f"User ID: {session.get('user_id')}, Status: {new_user}")

    users = User.query.all()
    if request.method == "POST":

        session.pop('user_id', None)
        username = request.form['username']
        password = request.form['password']

        try:
            user = [x for x in users if x.username == username][0]

            #if user typed in admin login and password, it will redirect to the admin page
            if username == "admin" and user.password == password:
                session['user_id'] = user.id
                session['username'] = user.username
                return redirect(url_for('admin'))

            #if user login and password is correct, it will redirect to the start of the game
            elif user and user.password == password:
                session['user_id'] = user.id
                return redirect(url_for('index'))

            #handles wrong password typed in
            else:
                new_user.clear()
                new_user.append(2)
                return redirect(url_for('login', new_user=new_user[0] ))
            
        #handles no such user typed in
        except:
            new_user.clear()
            new_user.append(1)
            return render_template('login.html', new_user=new_user[0])
        
    try:
        return render_template('login.html', new_user=new_user[0])
    except:
        new_user.clear()
        return render_template('login.html')

#The admin page
@app.route('/admin', methods=['POST', 'GET'])
@admin_login_required
def admin():
    users = User.query.all()
    return render_template('admin.html', users=users)

#The register new user page
@app.route('/register', methods=['POST', 'GET'])
def register():
    users = User.query.all()
    if request.method == "POST":
        session.pop('user_id', None)
        f_username = request.form['f_username']
        f_password = request.form['f_password']

       #checks if the user currently exists
        try:
            user = [x for x in users if x.username == f_username][0]
            new_user.clear()
            new_user.append(19)
            return redirect(url_for("login"))
        
        #adds the new user to the SQL database and redirects to the login page
        except:
            user = User(username=f_username,
                          password= f_password,
                          )
            db.session.add(user)
            db.session.commit()
            print("new user added")
            new_user.clear()
            new_user.append(20)
            return redirect(url_for("login"))

    return render_template('register.html')

# The delete user page
@app.route('/delete/', methods=['POST', 'GET'])
def delete():
    users = User.query.all()
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        try:
            user = [x for x in users if x.username == username][0]
            
            #password is correct, deleting the account
            if user and user.password == password:   
                user_del = User.query.get_or_404(user.id) 
                db.session.delete(user_del)
                db.session.commit()
                new_user.clear()
                new_user.append(7)
                return redirect(url_for('login', new_user=new_user[0]))
            
            #password incorrect, up to two more chances to type the correct one
            elif try_del_value.value < 3:     
                new_user.clear()
                new_user.append(8)
                del_try()
                return render_template('delete.html', new_user=new_user[0])

            #password incorrect, no more tries left. Redirects to the login page
            else:                          
                new_user.clear()
                new_user.append(9)
                return render_template('login.html', new_user=new_user[0])

        #No such user in the database, up to two more tries again
        except:                                
            new_user.clear()
            new_user.append(8)
            del_try()
            return redirect(url_for('delete'))
    return render_template('delete.html')

#The method to delete from the admin panel
@app.post('/delete_by_id/')
def delete_by_id():
     userID = request.args.get('user_id')
     user = User.query.get_or_404(userID)
     db.session.delete(user)
     db.session.commit()
     return redirect(url_for('admin'))

#Logout method
@app.route('/logout/')
def logout():
     session.pop('user_id', None)
     session.clear()
     new_user.clear()
     return redirect(url_for('login',new_user=None))

#Index page that loads starting values for the game
@app.route('/index', methods=['POST', 'GET'])
def index():
    # "setup" the session with starting values
    session['room_name'] = planisphere.START
    return redirect(url_for("game"))

#The starting game page with the game engine
@app.route("/game", methods=['GET', 'POST'])
@login_req
def game():
    users = User.query.all()
    room_name = session.get('room_name')

    if request.method == "GET":

        if room_name:
            room = planisphere.load_room(room_name)
            return render_template("show_room.html", room=room)
        else:
            return render_template("you_died.html")

    else:
        #loads the next room based on the user choice in the game
        action = request.form.get('action')

        if room_name and action:
            room = planisphere.load_room(room_name)
            next_room = room.go(action)

            if not next_room:
                session['room_name'] = planisphere.name_room(room)
            else:
                session['room_name'] = planisphere.name_room(next_room)

        return redirect(url_for("game"))

app.secret_key = 'A0Zr98j/ZZz R~XHH!jmNULWX/,?RT'

if __name__ == "__main__":
    app.run()
