from flask import Flask, render_template, request, redirect, session
from flask_paginate import Pagination, get_page_parameter
from flask_wtf.csrf import CSRFProtect
import datetime
from flask_pymongo import pymongo
from bson import ObjectId
import os


CONNECTION_STRING = "mongodb+srv://patrikhorvath2:auticko123@ukf.cxxnmkn.mongodb.net/?retryWrites=true&w=majority"

client = pymongo.MongoClient(CONNECTION_STRING)
db = client.get_database('blog')
article_collection = pymongo.collection.Collection(db, 'articles')
comment_collection = pymongo.collection.Collection(db, 'comments')


app = Flask(__name__)
csrf = CSRFProtect(app)
app.secret_key = os.urandom(12).hex()
app.config['UPLOAD_FOLDER'] = 'static/thumbnails'

@app.route('/')
def show():
    articles = []
    for article in db.articles.find():
        article['author'] = str(article['author'])
        articles.append(article)

    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 6
    offset = (page - 1) * per_page
    paginateditems = articles[offset:offset + per_page]

    pagination = Pagination(page=page, total=len(articles), record_name='articles', css_framework='bootstrap5', per_page=per_page)
    return render_template('index.html', articles=paginateditems, pagination=pagination)

@app.route('/login', methods=('GET', 'POST'))
@csrf.exempt
def login():
    if '_id' in session:
        return redirect('/')
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        user = db.users.find_one({"username": username, "password": password})
        if user:
            session['_id'] = str(user['_id'])
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            return redirect('/')
        else: 
            return render_template('login.html', error='Incorrect username or password')
    else:
        return render_template('login.html')

@app.route('/register', methods=('GET', 'POST'))
@csrf.exempt
def register():
    if '_id' in session:
        return redirect('/')
    if request.method=='POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            return render_template('register.html', error='Password and confirm password must be the same')
        if db.users.find_one({"username": username}):
            return render_template('register.html', error='Username is already taken')
        if db.users.find_one({"email": email}):
            return render_template('register.html', error='Email is already taken')
        db.users.insert_one(
        {
            "_id": ObjectId(),
            "username": username,
            "email": email,
            "password": password,
            "is_admin": False,
        })
        return render_template('login.html', success='Registration successful. You can now log in.')
    else:
        return render_template('register.html')
    
@app.route('/logout')
def logout():
    if not '_id' in session:
        return redirect('/')
    session.pop('username', None)
    session.pop('_id', None)
    session.pop('is_admin', None)
    return redirect('/')

@app.route('/create', methods=('GET', 'POST'))
@csrf.exempt
def create():
    if '_id' not in session:
        return redirect('/login')
    if request.method=='POST':
        _id = ObjectId()
        title = request.form['title']
        date = request.form['date']
        text = request.form['body']
        author = db.users.find_one({"username": session['username']})['_id']
        file = request.files['thumbnail']
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], str(_id) + '.jpg'))
        article_collection.insert_one(
        {
            "_id": _id,
            "title": title,
            "date": date,
            "body": text,
            "author": author
        })
        return redirect('/') 
    else: 
        return render_template("create.html") 

@app.route("/delete/<string:_id>/", methods=('GET', 'POST'))
@csrf.exempt
def delete(_id):
    if '_id' not in session:
        return redirect('/login')
    author = db.articles.find_one({"_id": ObjectId(_id)})['author']
    if session['_id']==str(author) or session['is_admin']:
        obj_id = ObjectId(_id)
        article_collection.delete_one({"_id": obj_id})
    return redirect('/')

@app.route('/edit/<string:_id>/', methods=('GET', 'POST'))
@csrf.exempt
def edit(_id):
    article = db.articles.find_one({"_id": ObjectId(_id)})
    if '_id' not in session:
        return redirect('/login')
    if str(article['author'])!=session['_id'] and not session['is_admin']:
        return redirect('/')
    if request.method=='POST':
        _id = ObjectId(_id)
        title = request.form['title']
        date = request.form['date']
        text = request.form['body']
        if request.files['thumbnail'].filename!='':
            file = request.files['thumbnail']
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], str(_id) + '.jpg'))
        article_collection.update_one({"_id": _id},
        {'$set': {
            "_id": _id,
            "title": title,
            "date": date,
            "body": text
        }})
        return redirect('/') 
    else: 
        return render_template("edit.html", article = article) 
    
@app.route('/<string:_id>/')
def show_article(_id):
    article = db.articles.find_one({"_id": ObjectId(_id)})
    article['author'] = str(article['author'])
    comments_cursor = db.comments.find({"article": ObjectId(_id)})
    comments = []
    for comment in comments_cursor:
        comment['author'] = db.users.find_one({"_id": comment['author']})['username']
        comments.append(comment)
    article['authorname'] = db.users.find_one({"_id": ObjectId(article['author'])})['username']
    return render_template('article.html', article=article, comments=comments)

@app.route('/add_comment/<string:_id>/', methods=['POST'])
@csrf.exempt
def add_comment(_id):
    if '_id' not in session:
        return redirect('/login')
    _id = ObjectId(_id)
    text = request.form['text']
    author = session['_id']
    comment_collection.insert_one(
    {
        "_id": ObjectId(),
        "text": text,
        "article": _id,
        "author": ObjectId(author),
        "date": datetime.datetime.now()
    })
    return redirect('/' + str(_id)) 

@app.route('/admin/', methods=('GET', 'POST'))
@csrf.exempt
def admin():
    if '_id' not in session:
        return redirect('/login')
    if not session['is_admin']:
        return redirect('/')
    else:
        users = []
        for user in db.users.find():
            users.append(user)
        return render_template('admin.html', users=users)
    
@app.route('/admin/edit/<string:_id>/', methods=('GET', 'POST'))
@csrf.exempt
def admin_edit(_id):
    if '_id' not in session:
        return redirect('/login')
    if not session['is_admin']:
        return redirect('/')
    if session['_id']==_id:
        return redirect('/admin')
    else:
        is_admin = request.form.get('is_admin')
        if is_admin=='on':
            is_admin = True
        else:
            is_admin = False
        db.users.update_one({"_id": ObjectId(_id)},
        {'$set': {
            "is_admin": is_admin
        }})
        return redirect('/admin')

@app.route('/admin/delete/<string:_id>/', methods=('GET', 'POST'))
@csrf.exempt
def admin_delete(_id):
    if '_id' not in session:
        return redirect('/login')
    if not session['is_admin']:
        return redirect('/')
    if session['_id']==_id:
        return redirect('/admin')
    else:
        obj_id = ObjectId(_id)
        db.users.delete_one({"_id": obj_id})
        return redirect('/admin')