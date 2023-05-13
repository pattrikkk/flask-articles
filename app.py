from flask import Flask, render_template, request, redirect, session
import datetime
from flask_pymongo import pymongo
from bson import ObjectId


CONNECTION_STRING = "mongodb+srv://patrikhorvath2:auticko123@ukf.cxxnmkn.mongodb.net/?retryWrites=true&w=majority"

client = pymongo.MongoClient(CONNECTION_STRING)
db = client.get_database('blog')
article_collection = pymongo.collection.Collection(db, 'articles')
comment_collection = pymongo.collection.Collection(db, 'comments')


app = Flask(__name__)
app.secret_key = 'RrGbtgj71ohV5cr195HgElCDC6amRlN3'

@app.route('/')
def show():
    articles = []
    for article in db.articles.find():
        article['author'] = str(article['author'])
        articles.append(article)

    return render_template('index.html', articles=articles)

@app.route('/login', methods=('GET', 'POST'))
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
            return redirect('/')
        else: 
            return render_template('login.html', error='Incorrect username or password')
    else:
        return render_template('login.html')

@app.route('/register', methods=('GET', 'POST'))
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
            "password": password
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
    return redirect('/')

@app.route('/create', methods=('GET', 'POST'))
def create():
    if '_id' not in session:
        return redirect('/login')
    if request.method=='POST':
        _id = ObjectId()
        title = request.form['title']
        date = request.form['date']
        text = request.form['body']
        author = db.users.find_one({"username": session['username']})['_id']
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
def delete(_id):
    if '_id' not in session:
        return redirect('/login')
    author = db.articles.find_one({"_id": ObjectId(_id)})['author']
    if session['_id']==str(author):
        obj_id = ObjectId(_id)
        article_collection.delete_one({"_id": obj_id})
    return redirect('/')

@app.route('/edit/<string:_id>/', methods=('GET', 'POST'))
def edit(_id):
    article = db.articles.find_one({"_id": ObjectId(_id)})
    if '_id' not in session:
        return redirect('/login')
    if str(article['author'])!=session['_id']:
        return redirect('/')
    if request.method=='POST':
        _id = ObjectId(_id)
        title = request.form['title']
        date = request.form['date']
        text = request.form['body']
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
    return render_template('article.html', article=article, comments=comments)

@app.route('/add_comment/<string:_id>/', methods=['POST'])
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