import json
import logging
import math
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from flask import Flask, request, redirect, flash, session, render_template
from werkzeug.utils import secure_filename
# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))


app = Flask(__name__)

# Set the upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Make sure the folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Build the path to the 'config.json' file located in the 'templates' folder
config_path = os.path.join(script_dir, 'templates', 'config.json')

# Load the configuration file
with open(config_path, 'r') as c:
    params = json.load(c)["params"]

local_server = True
# Set a secret key for session management
app.config['SECRET_KEY'] = os.urandom(24)  # You can also hardcode a random string for simplicity.

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params["gmail_user"],
    MAIL_PASSWORD=params["gmail_password"],
)

mail = Mail(app)

if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['remote_uri']

db = SQLAlchemy(app)

# Define the models for Users and Posts
class Users(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(255), unique=True, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    message = db.Column(db.String(255), nullable=False)

class Posts(db.Model):
    __tablename__ = 'posts'
    s_no = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(2048), nullable=False)
    content = db.Column(db.String(2048), nullable=False)
    subHeading = db.Column(db.String(2048), nullable=False)
    postedBy = db.Column(db.String(255), nullable=False)
    postDate = db.Column(db.DateTime, default=datetime.utcnow)
    slug = db.Column(db.String(255), nullable=False)
    bg_image = db.Column(db.String(255), nullable=True)

# Define routes
# @app.route('/')
# def blog():
#     posts = Posts.query.filter_by().all()[0:5]
#     return render_template('index.html', params=params, posts=posts)

# @app.route('/')
# def home():
#     posts = Posts.query.filter_by().all()
#     last = int(math.ceil(len(posts)//int(params['no_of_posts'])))
#     page = request.args.get('page')
#     # Initialize prev and next with default values
#
#     if (not str(page).isnumeric() ):
#         page = 1
#         page = int(page)
#         # posts = posts[page * params['no_of_posts']:(page + 1) * params['no_of_posts']]
#         posts = posts[(page-1) * int(params['no_of_posts']): (page-1) * int(params['no_of_posts']) + int(params['no_of_posts'])]
#
#         if page == 1:
#             prev= "#"
#             next = "/?page=" + str(page+1)
#         elif page == last:
#             prev = "/?page=" + str(page-1)
#             next = "#"
#         else:
#             prev = "/?page=" + str(page-1)
#             next = "/?page=" + str(page+1)
#
#
#
#     return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route('/')
def home():
    # Query all posts from the database
    posts = Posts.query.all()  # Ensure 'Posts' is defined and imported
    per_page = int(params['no_of_posts'])  # Number of posts per page
    total_posts = len(posts)  # Total number of posts
    last = math.ceil(total_posts / per_page)  # Total number of pages

    # Get the current page from request arguments, default to 1
    page = request.args.get('page', default=1, type=int)

    # Validate page number
    if page < 1:
        page = 1
    elif page > last:
        page = last

    # Slice posts for the current page
    start = (page - 1) * per_page
    end = start + per_page
    paginated_posts = posts[start:end]

    # Set navigation links
    prev = f"/?page={page - 1}" if page > 1 else None
    next = f"/?page={page + 1}" if page < last else None

    # Render the template with paginated posts and navigation links
    return render_template('index.html', params=params, posts=paginated_posts, prev=prev, next=next)
@app.route("/post/<string:post_slug>", methods=['GET', 'POST'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)

@app.route('/contact', methods=['POST', 'GET'])
def contact():
    try:
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            message = request.form['message']

            # Create a new user entry
            entry = Users(name=name, email=email, phone=phone, message=message)
            db.session.add(entry)
            db.session.commit()
            mail.send_message("New Message from Blog", sender=email, recipients=[params['gmail_user']],
                              body=message + "\n" + phone + "\n" + name)

            return render_template('contact.html', success=True, params=params)
        else:
            return render_template('contact.html', params=params)
    except Exception as e:
        return f"An error occurred: {e}", 500

@app.route('/about')
def about():
    return render_template('about.html', params=params)

@app.route('/contact_us', methods=['POST', 'GET'])
def contact_us():
    return render_template('contact.html', params=params)

@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    if 'user' in session and session['user'] == params['admin_user']:
        posts= Posts.query.all()
        return render_template('dashboard.html',posts=posts, params=params)

    if request.method == 'POST':
        username = request.form['user_email']
        password = request.form['user_pass']

        if username == params['admin_user'] and password == params['admin_password']:
            session['user'] = username
            posts = Posts.query.all()
            return render_template('dashboard.html',posts=posts, params=params)

    return render_template('login.html', params=params)
@app.route('/delete/<string:s_no>', methods=['POST', 'GET'])
def delete(s_no):
    if 'user' in session and session['user'] == params['admin_user']:
        post = Posts.query.filter_by(s_no=s_no).first()
        db.session.delete(post)
        db.session.commit()
        return redirect('/dashboard')

@app.route('/edit/<string:s_no>', methods=['POST', 'GET'])
def edit_with_id(s_no):
    if 'user' in session and session['user'] == params['admin_user']:
        # Handle the case where s_no is '0' (i.e., creating a new post)
        if s_no == '0':
            post = None
        else:
            post = Posts.query.filter_by(s_no=s_no).first()

        if request.method == 'POST':
            box_title = request.form['title']
            tagline = request.form['subHeading']
            content = request.form['content']
            slug = request.form['slug']
            bg_image = request.form['bg_image']
            posted_by = session.get('user')  # Get the logged-in username
            post_date = datetime.now()

            # Ensure `posted_by` is not null
            if posted_by is None:
                return "Error: No user logged in to post", 400  # Return error if user not found

            if s_no == '0':  # New post
                new_post = Posts(
                    title=box_title,
                    subHeading=tagline,
                    content=content,
                    slug=slug,
                    bg_image=bg_image,
                    postedBy=posted_by,  # Assign the username to postedBy
                    postDate=post_date
                )
                db.session.add(new_post)
                db.session.commit()

                # After adding the new post, redirect to its edit page
                return redirect(f'/edit/{new_post.s_no}')

            else:  # Editing existing post
                if post:
                    post.title = box_title
                    post.subHeading = tagline
                    post.content = content
                    post.slug = slug
                    post.bg_image = bg_image
                    post.postedBy = posted_by  # Assign the username to postedBy
                    post.postDate = post_date
                    db.session.commit()

                return redirect(f'/edit/{s_no}')

        # If it's a GET request, render the edit page
        return render_template('edit.html', params=params, post=post)

    return "Post not found", 404

@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove 'user' from session
    return redirect('/dashboard')

# @app.route("/uploader", methods=['GET','POST'])
# def uploader_fun():
#     if 'user' in session and session['user'] == params['admin_user']:
#         if request.method == 'POST':
#             file = request.files['postFile']
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
#             return redirect(f'/dashboard')


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def save_file(file, upload_folder):
    try:
        filename = secure_filename(file.filename)
        file.save(os.path.join(upload_folder, filename))
        return filename
    except Exception as e:
        logging.exception("Error saving file: %s", e)
        return None

@app.route("/uploader", methods=['GET', 'POST'])
def uploader_fun():
    if 'user' in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            file = request.files.get('postFile')
            if not file or file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)

            if allowed_file(file.filename):
                filename = save_file(file, app.config['UPLOAD_FOLDER'])
                if filename:
                    flash(f'File "{filename}" successfully uploaded', 'success')
                else:
                    flash('Failed to upload file', 'error')
            else:
                flash('Invalid file type', 'error')
            return redirect('/dashboard')
        return render_template('Dashboard.html', params=params)

    return redirect('/login')

@app.route('/post')
def posts_route():
    return render_template('post.html', params=params)

@app.route('/post/<int:post_id>')
def post_with_id(post_id):
    post = Posts.query.get(post_id)
    if not post:
        return "Post not found", 404
    return render_template('post.html', params=params, post=post)

if __name__ == '__main__':
    app.run(debug=True)
