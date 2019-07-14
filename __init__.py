from flask import Flask, render_template, flash, request, url_for, redirect, session, json, jsonify
from flask import send_from_directory
from wtforms import Form, BooleanField, TextField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from MySQLdb import escape_string as thwart
from dbconnect import connection
from werkzeug.utils import secure_filename
import gc
import os
import itertools

UPLOAD_FOLDER = '/var/www/FlaskApp/FlaskApp/static/images'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def currentMovieMap(form, filename):
    currentMovie= {}
    currentMovie["Title"] = form["Title"]
    currentMovie["StoryLine"] = form["StoryLine"]
    currentMovie["ReleaseDate"] = form["ReleaseDate"]
    currentMovie["Language"] = form["Language"]
    currentMovie["cast"] = form["Cast"].split(",")
    currentMovie["character"] = form["character"].split(",")
    currentMovie["genre"] = form["Genre"].split(",")
    currentMovie["age"] = form["age"]
    currentMovie["keywords"] = form["keywords"].split(",")
    currentMovie["filename"] = filename
    return currentMovie

def currentSeriesMap(form, filename):
    currentSeries= {}
    currentSeries["TVTitle"] = form["TVTitle"]
    currentSeries["TVStoryLine"] = form["TVStoryLine"]
    currentSeries["TVReleaseDate"] = form["TVReleaseDate"]
    currentSeries["TVLanguage"] = form["TVLanguage"]
    currentSeries["TVcast"] = form["TVCast"].split(",")
    currentSeries["TVcharacter"] = form["TVcharacter"].split(",")
    currentSeries["TVgenre"] = form["TVGenre"].split(",")
    currentSeries["TVkeywords"] = form["TVkeywords"].split(",")
    currentSeries["filename"] = filename
    return currentSeries

with open('/var/www/FlaskApp/FlaskApp/static/movies.json') as in_file:
    data = json.load(in_file)
    in_file.close()

with open('/var/www/FlaskApp/FlaskApp/static/tv.json') as in_filetv:
    tvdata = json.load(in_filetv)
    in_filetv.close()

@app.route('/', methods=['GET', 'POST'])
def homepage():
    return render_template("main.html", data=data)

@app.route('/tv/', methods=['GET', 'POST'])
def tvpage():
    return render_template("tv.html", tvdata=tvdata)

@app.route('/about/')
def aboutpage():
    return render_template("about.html")

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("You need to login first")
            return redirect(url_for('login_page'))
    return wrap

@app.route("/logout/")
@login_required
def logout():
    session.clear()
    flash("You have been logged out!")
    gc.collect()
    return redirect(url_for('homepage'))

@app.route("/upload/", methods=["GET","POST"])
@login_required
def upload():
    if request.method == "POST" and "filename" in request.files:
        file = request.files['filename']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    if request.method == "POST" and "Title" in request.form:
        data[request.form["Title"]] = currentMovieMap(request.form, filename)
        with open('/var/www/FlaskApp/FlaskApp/static/movies.json', 'w') as outfile:
            json.dump(data, outfile)
        flash("Your Submission Has Been Submitted For Review, Thanks For Contributing!")
        return render_template("main.html", data=data, filename=filename)
    return render_template("upload.html", data=data)


@app.route("/tvupload/", methods=["GET","POST"])
@login_required
def tvupload():
    if request.method == "POST" and "filename" in request.files:
        file = request.files['filename']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    if request.method == "POST" and "TVTitle" in request.form:
        tvdata[request.form["TVTitle"]] = currentSeriesMap(request.form, filename)
        with open('/var/www/FlaskApp/FlaskApp/static/tv.json', 'w') as outfile:
            json.dump(tvdata, outfile)
        flash("Your Submission Has Been Submitted For Review, Thanks For Contributing!")
        return render_template("tv.html", tvdata=tvdata, filename=filename)
    return render_template("tvupload.html", tvdata=tvdata)

@app.route("/datareview/", methods=["GET","POST"])
@login_required
def datareview():
    return render_template("datareview.html")

@app.route('/login/', methods=["GET","POST"])
def login_page():
    try:
        c, conn = connection()

        error = None
        if request.method == "POST":
            data = c.execute("SELECT * FROM users WHERE username = (%s)",
                             [thwart(request.form['username'])])
            data = c.fetchone()[2]

            if sha256_crypt.verify(request.form['password'], data):
                session['logged_in'] = True
                session['username'] = request.form['username']

                flash("You are now logged in")
                return redirect(url_for("homepage"))
            else:
                error = "Invalid Username or Password, try again."

        gc.collect()
        return render_template("login.html", error=error)
    except Exception as e:
        error = "Invalid credentials, try again."
        return render_template("login.html", error = error)

class RegistrationForm(Form):
    username = TextField('Username', [validators.Length(min=4, max=25)])
    email = TextField('Email Address', [validators.Length(min=6, max=35)])
    password = PasswordField('New Password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    accept_tos = BooleanField('I accept the TOS', [validators.Required()])

@app.route('/signup/', methods=["GET","POST"])
def signup_page():
    try:
        form = RegistrationForm(request.form)
        if request.method == "POST" and form.validate():
            username  = form.username.data
            email = form.email.data
            password = sha256_crypt.encrypt((str(form.password.data)))
            c, conn = connection()
            x = c.execute("SELECT * FROM users WHERE username = (%s)", (username,))
            if int(x) > 0:
                flash("That username is already taken, please choose another")
                return render_template('signup.html', form=form)
            else:
                c.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
                          (thwart(username), thwart(password), thwart(email)))
                conn.commit()
                flash("Thanks for registering!")
                c.close()
                conn.close()
                gc.collect()

                session['logged_in'] = True
                session['username'] = username

                return redirect(url_for('homepage'))

        return render_template("signup.html", form=form)

    except Exception as e:
        return(str(e))


@app.route('/movies/<currentMovie>/', methods=["GET","POST"])
def currentMovie(currentMovie):
        cast = data[currentMovie]["cast"]
        char = data[currentMovie]["character"]
	return render_template("currentMovie.html", data=data, currentMovie=currentMovie, castchar=zip(cast,char))

@app.route('/tv/<currentSeries>/', methods=["GET","POST"])
def currentSeries(currentSeries):
        TVcast = tvdata[currentSeries]["TVcast"]
        TVchar = tvdata[currentSeries]["TVcharacter"]
	return render_template("currentSeries.html", tvdata=tvdata, currentSeries=currentSeries, TVcastchar=zip(TVcast,TVchar))


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html")

@app.errorhandler(500)
def page_not_found(e):
    return render_template("500.html")

if __name__ == "__main__":
     app.debug = True
     app.run()
