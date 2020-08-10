from flask import Flask, g, render_template,flash,redirect,url_for,session,logging,request, send_from_directory
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import os
from werkzeug.utils import secure_filename

#Kullanıcı Giriş Decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapmalısınız.", "danger")
            return redirect(url_for("login"))
    return decorated_function

#Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField('İsim ve Soyisim:',validators = [validators.InputRequired("Bu alan boş bırakılamaz."), validators.Length(min=4,max=25)])
    username = StringField('Kullanıcı Adı:',validators = [validators.InputRequired("Bu alan boş bırakılamaz."), validators.Length(min=5,max=15)])
    email = StringField('Email:',validators = [validators.InputRequired("Bu alan boş bırakılamaz."), validators.Length(min=10,max=25), validators.Email("Geçerli bir e-mail adresi giriniz")])
    password = PasswordField("Parola:", validators = [validators.InputRequired("Bu alan boş bırakılamaz."),validators.EqualTo(fieldname= "confirm",message="Parolalar uyuşmuyor!")])
    confirm = PasswordField("Parola Tekar:")

app = Flask(__name__, static_url_path='/static')
UPLOAD_FOLDER = 'C:/Users/Casper/PycharmProjects/Projelerim/Blog/static'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "battalblog"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "battalblog2"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

APP_ROUTE = os.path.dirname(os.path.abspath(__file__))

mysql = MySQL(app)

#Statik Dosya yolu oluşturmak
@app.route('/profile')
def root():
    return app.send_static_file('profile.html')

#Makale Oluşturma Formu
class ArticleForm(Form):
    title = StringField("Makale Başlığı:", validators = [validators.Length(min=8, max=100)])
    content = TextAreaField("Makale İçeriği:",validators = [validators.Length(min=10)])

class LoginForm(Form):
    username = StringField("Kullanıcı Adı:")
    password = PasswordField("Parola:")



@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

#Kayıt olma
@app.route("/register",methods = ["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO USERS(name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()

        flash("Başarıyla Kayıt oldunuz!", "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)

#Login İşlemi
@app.route("/login",methods= ["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(sorgu,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla giriş yaptınız!","success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Parolanız yanlış girildi!","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor!", "danger")
            return redirect(url_for("login"))
    else:
        return render_template("login.html",form=form)
#Logout İşlemi
@app.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for("index"))

#Kontrol Paneli
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(sorgu,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")

@app.route("/addarticle",methods= ["GET", "POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST":
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO articles(title,author,content) VALUES (%s,%s,%s)"
        cursor.execute(sorgu,(title, session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarıyla eklendi.", "success")
        return redirect(url_for("dashboard"))

    else:
        return render_template("addarticle.html",form=form)

#Makale Sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")

#Detay Sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(sorgu,(id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")

#Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Makele yok veya bu makaleyi silme yetkiniz yok.","danger")
        return redirect(url_for("index"))

#Makale Güncelleme
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))
        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok.","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form=form)
    else:
        #POST REQUEST
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()

        flash("Makale başarıyla güncellendi.", "success")
        return redirect(url_for("dashboard"))
#Arama URL
@app.route("/search",methods=["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE title LIKE '%" + keyword + "%'"
        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı.","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles=articles)

#Profil Sayfası
@app.route("/profil")
@login_required
def profil():
    return render_template("profil.html")

@app.route("/myfiles")
@login_required
def myfiles():
    return render_template("myfiles.html")

#Dosya kontrolü
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Dosya yüklemek
@app.route('/profil', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part','danger')
            return redirect(url_for("profil"))
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', "warning")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            cursor = mysql.connection.cursor()
            sorgu = "UPDATE users SET images = %s WHERE username = %s"
            cursor.execute(sorgu,(filename,session['username']))
            mysql.connection.commit()

            flash("Successful", "success")
            return render_template("profil.html",user_image = filename)

@app.route("/upload")
def upload():
    return render_template("upload.html")

@app.route("/upload_root",methods= ["POST"])
def upload_root():
    target = os.path.join(APP_ROUTE, 'images/')
    print(target)

    if not os.path.isdir(target):
        os.mkdir(target)
    for file in request.files.getlist("file"):
        print(file)
        filename = file.filename
        destination = "/".join([target,filename])
        print(destination)
        file.save(destination)
    return render_template("complete.html")

if __name__ == "__main__":
    app.run(debug=True)

