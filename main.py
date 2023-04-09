from flask import Flask, render_template, request, flash, redirect, url_for, session, abort
import sqlite3 as sql
from bs4 import BeautifulSoup
import requests
import lxml

DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = 'MN76MN$^6MTmt6@#m6jj0h%65tj^h6nht65NHrn75tj6T^'


def createUsersDb():
    con = sql.connect('users.db')
    cur = con.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS users 
    (name TEXT, psw TEXT, avatarPath TEXT, countOfPosts BIGINT)
    ''')
    con.commit()


def createPostsDb():
    con = sql.connect('posts.db')
    cur = con.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS posts
    (title TEXT, content TEXT, author TEXT)
    ''')

    con.commit()


createUsersDb()
createPostsDb()


@app.route('/', methods=['POST', 'GET'])
@app.route('/index', methods=['POST', 'GET'])
def index():
    con = sql.connect('users.db')
    cur = con.cursor()
    usernames = cur.execute('''SELECT name FROM users''').fetchall()
    avatarPaths = cur.execute('''SELECT avatarPath FROM users''').fetchall()
    countOfPosts = cur.execute('''SELECT countOfPosts FROM users''').fetchall()

    return render_template('index.html',
                           usernames=usernames,
                           avatarPaths=avatarPaths,
                           countOfPosts=countOfPosts,
                           usersCount=len(usernames))


@app.route('/about', methods=['POST', 'GET'])
def about():
    return render_template('about.html')


@app.route('/reg', methods=['POST', 'GET'])
def reg():
    if 'userLogged' in session:
        return redirect(url_for('acc', name=session['userLogged']))
    elif request.method == 'POST':

        name = request.form['name']
        psw = request.form['psw']

        if len(name) >= 4 and len(psw) >= 4 and ('"' not in name) and ('"' not in psw):

            if not checkUserExistence(name=name) and name != 'NONE':

                con = sql.connect('users.db')
                cur = con.cursor()
                cur.execute(f'''INSERT INTO users 
                            (name, psw, avatarPath, countOfPosts) 
                            VALUES ("{name}", "{psw}", "NONE.jpg", 0) ''')
                con.commit()
                session['userLogged'] = request.form['name']
                return redirect(url_for('acc', name=session['userLogged']))
            else:
                session.clear()
                flash('This name is already occupied')
        else:
            flash('Psw and name must be 4 or more chars length, and not include \' or "')

    return render_template('reg.html')


@app.route('/acc/<name>', methods=['POST', 'GET'])
def acc(name):
    # preventing user from authorize without password
    if 'userLogged' not in session:
        abort(401)
    if name != session['userLogged']:
        abort(401)
    name = session['userLogged']

    # get images from db
    con = sql.connect('users.db')
    cur = con.cursor()
    avatarPath = cur.execute(f'''SELECT avatarPath FROM users WHERE name = "{name}"''').fetchone()[0]
    countOfPosts = cur.execute(f'''SELECT countOfPosts FROM users WHERE name = "{name}"''').fetchone()[0]

    if request.method == 'POST':
        try:
            # get images from GitHub account
            response = requests.get(request.form['git-url'])
            soup = BeautifulSoup(response.text, 'lxml')
            url = str(soup.find(
                'img', {'class': 'rounded-2 avatar-user'})
                ).split('src="')[1].split('"')[0].split('?s=')[0]
            resp = requests.get(url)
            out = open(f"static/media/avatars/{name}.jpg", "wb")
            out.write(resp.content)
            out.close()

            # Update avatar path in db
            con = sql.connect('users.db')
            cur = con.cursor()
            cur.execute(f'UPDATE users SET avatarPath = "{name}.jpg" WHERE name = "{name}"')
            avatarPath = cur.execute(f'''SELECT avatarPath FROM users WHERE name = "{name}"''').fetchone()[0]
            con.commit()


            return render_template('acc.html', name=name, avatarPath=avatarPath, countOfPosts=countOfPosts)

        except ValueError:
            # flash about unfounded GitHub account
            flash("Such GitHub account doesn't exists")

    return render_template('acc.html', name=name, avatarPath=avatarPath, countOfPosts=countOfPosts)


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    return redirect(url_for('reg'))


@app.route('/auth', methods=['POST', 'GET'])
def auth():
    if request.method == 'POST':
        name = request.form['name']
        psw = request.form['psw']

        if not checkUserExistence(name=name):
            session.clear()
            flash("This account doesn't exists")
        else:
            if checkAuth(name=name, psw=psw):
                session['userLogged'] = request.form['name']
                return redirect(url_for('acc', name=session['userLogged']))
            else:
                session.clear()
                flash('Incorrect login or password')
    return render_template('auth.html')


@app.route('/acc/<name>/add-post', methods=['POST', 'GET'])
def addPost(name):

    if 'userLogged' not in session:
        abort(401)
    if name != session['userLogged']:
        abort(401)

    name = session['userLogged']

    if request.method == 'POST':

        title = request.form['title']
        content = request.form['content']

        if ('"' not in title) and ("'" not in title) and ("'" not in content) and ('"' not in content):

            con = sql.connect('posts.db')
            cur = con.cursor()

            cur.execute(f'''INSERT INTO posts (title, content, author) VALUES ("{title}", "{content}", "{name}")''')
            con.commit()

            con = sql.connect('users.db')
            cur = con.cursor()

            countOfPosts = cur.execute(f'''SELECT countOfPosts FROM users WHERE name = "{name}"''').fetchone()[0]
            cur.execute(f'''UPDATE users SET countOfPosts = {countOfPosts + 1} WHERE name = "{name}"''')
            con.commit()

        else:
            flash('content and title must be 4 or more chars length, and not include \' or "')

    return render_template('add-post.html')


@app.route('/<name>/posts')
def posts(name):
    if checkUserExistence(name=name):
        if checkPostsExistence(name=name):
            # get images from db
            con = sql.connect('users.db')
            cur = con.cursor()
            avatarPath = cur.execute(f'''SELECT avatarPath FROM users WHERE name = "{name}"''').fetchone()[0]

            con = sql.connect('posts.db')
            cur = con.cursor()
            titles = cur.execute(f'''SELECT title FROM posts WHERE author = "{name}"''').fetchall()
            contents = cur.execute(f'''SELECT content FROM posts WHERE author = "{name}"''').fetchall()
            postsCount = len(contents)
            print(postsCount)

            if 'userLogged' in session:
                username = session['userLogged']
            else:
                username = None

            return render_template('posts.html',
                                   name=name,
                                   avatarPath=avatarPath,
                                   titles=titles, contents=contents,
                                   postsCount=postsCount,
                                   username=username)
        else:
            return redirect(url_for('postsNotFound', name=name))
    else:
        return redirect(url_for('userNotFound'))


@app.route('/<name>/profile')
def profile(name):
    if checkUserExistence(name=name):
        # get images from db
        con = sql.connect('users.db')
        cur = con.cursor()
        avatarPath = cur.execute(f'''SELECT avatarPath FROM users WHERE name = "{name}"''').fetchone()[0]
        countOfPosts = cur.execute(f'''SELECT countOfPosts FROM users WHERE name = "{name}"''').fetchone()[0]

        return render_template('profile.html', name=name, avatarPath=avatarPath, countOfPosts=countOfPosts)
    else:
        return redirect(url_for('userNotFound'))


@app.route('/error:user-not-found')
def userNotFound():
    return render_template('userNotFound.html')


@app.route('/<name>/posts-not-found')
def postsNotFound(name):
    return render_template('postsNotFound.html', name=name)


@app.errorhandler(401)
def error401redir(error):
    return redirect(url_for('error401page'))


@app.route('/error:401')
def error401page():
    return render_template('error401.html')


@app.errorhandler(404)
def error404redir(error):
    return redirect(url_for('error404page'))


@app.route('/error:404')
def error404page():
    return render_template('error404.html')


def checkUserExistence(name):
    con = sql.connect('users.db')
    cur = con.cursor()
    checker = False

    for userName in cur.execute('''SELECT name FROM users'''):
        if name == userName[0]:
            checker = True
            break
        else:
            checker = False
    return checker


def checkPostsExistence(name):
    con = sql.connect('posts.db')
    cur = con.cursor()
    checker = False

    for userName in cur.execute('''SELECT author FROM posts'''):
        if name == userName[0]:
            checker = True
            break
        else:
            checker = False
    return checker


def checkPostExistence(name, title):
    con = sql.connect('posts.db')
    cur = con.cursor()
    checker = False

    for userName in cur.execute(f'''SELECT author FROM posts WHERE title = "{title}"'''):
        if name == userName[0]:
            checker = True
            break
        else:
            checker = False
    print(checker)
    return checker


def checkAuth(name, psw):
    con = sql.connect('users.db')
    cur = con.cursor()

    if cur.execute(f'''SELECT psw FROM users WHERE name = "{name}"''').fetchall()[0][0] == psw:
        return True
    else:
        return False


@app.route('/deletepost/<name>:<title>')
def deletepost(name, title):

    if checkPostsExistence(name=name):
        if checkPostExistence(name=name, title=title):

            if 'userLogged' in session:
                if session['userLogged'] == name:

                    print(f'post {title} deleted')

                    con = sql.connect('posts.db')
                    cur = con.cursor()

                    cur.execute(f'''DELETE FROM posts WHERE title = "{title}" and author = "{name}" ''')
                    con.commit()

                    con = sql.connect('users.db')
                    cur = con.cursor()
                    countOfPosts = cur.execute(f'''SELECT countOfPosts FROM users 
                        WHERE name = "{name}"''').fetchone()[0]

                    cur.execute(f'''UPDATE users SET countOfPosts = {countOfPosts - 1} WHERE name = "{name}"''')
                    con.commit()

                    return redirect(url_for('posts', name=name))
                else:
                    abort(401)
            else:
                abort(401)

        else:
            abort(404)
        return redirect(url_for('posts', name=name))
    else:
        return redirect(url_for('userNotFound'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
