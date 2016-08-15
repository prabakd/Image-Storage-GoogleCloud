from pymongo import MongoClient
from flask import Flask,render_template,redirect,session,flash,request,url_for
from functools import wraps
import base64
import uuid
import os
from datetime import datetime,timedelta


app = Flask(__name__)
app.secret_key = "temp"
#app.permanent_session_lifetime = timedelta(minutes=10)
client = MongoClient('mongodb://HOST:PORT/')
db = client.image
usercoll=db.users
imgcoll=db.img

#### Login function 
def login_required(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            flash("YOU NEED TO LOGIN FIRST")
            return redirect(url_for('welcome'))
    return wrap



#### Welcome redirect function
@app.route('/')
def welcome():
    return render_template('welcome.html')

#### New user redirect to adduser.html
@app.route('/newuser')
def newuser():
    return render_template('adduser.html')

#### Add user function it will check whether the user already exists or not, if not the user will be added
@app.route('/adduser',methods=['POST','GET'])
def adduser():
    user = request.form['username']
    password = request.form['password']
    posts=usercoll.find_one({'username':user})
    print posts
    if posts:
        flash("USER ALREADY EXISTS")
        return redirect(url_for('newuser'))
    else:
        post = {'username': user, 'password': password, 'limit': 0}
        id=usercoll.insert_one(post).inserted_id
        flash ("User Added Successfully")
    return redirect(url_for('welcome'))


@app.route('/login')
def login():
    return render_template('login.html')

#### Will verify the credentials of the user
@app.route('/authenticate',methods=['POST','GET'])
def authenticate():
    error=""
    if request.method=='POST':
        username= request.form['username']
        password= request.form['password']
        posts = usercoll.find_one({'username': username})
        if not posts:
            error="User Doesnt Exits"
            return render_template('login.html',error=error)
        if posts:
            print posts
            fuser=posts['username']
            fpass=posts['password']
            if fpass==password:
                session['logged_in']=True
                session['username']=request.form['username']
                return render_template("menu.html")
            else:
                error="Invalid credentials"
                return render_template('login.html', error=error)
    return "PLS WAIT"



@app.route('/logout',methods=['POST','GET'])
def logout():
    session.pop('logged_in',None)
    session.pop('username', None)
    flash('YOU JUST LOGGED OUT')
    return redirect(url_for('welcome'))

### It will allow the current user to view his/her images alone
@app.route('/view')
@login_required
def view():
    username = session['username']
    posts = get_details_by_username(username)
    html_string = ""
    for post in posts:
        img1 = post['image_data']
        comments = post['comments']
        c_string = "<div><h5>Comments on Image </h5>"
        for comment in comments:
            c_string += "user:" + comment['username'] + "<br>" + "comment:" + comment['comment'] + "&nbsp&nbsp&nbsp&nbsp<a href=\"/deletecomment/"+post['post_id']+"/"+comment['comm_id']+"\">delete</a><br>"
        c_string += "</div>"
        decode = img1.decode()
        img_tag = '<img alt="sample" src="data:image/jpeg;base64,{0}">'.format(decode)
        post_id = "'" + post['post_id'] + "'"
        button_tag = "<form action=\"/delete/"+post['post_id']+"\" method=\"post\"><input type=\"submit\" value=\"Delete Image\"></form>"
        #comment_function = "\"comment('" + post['post_id'] + "')\""
        text_area="<form action=\"/comment/"+post['post_id']+"\" method=\"post\"><input type=\"textarea\" maxlength=\"250\" name=\"comm\"><input type=\"submit\" value=\"post\"></form>"
        #comment_tag = "<a id='comment' href='#commentmodal' role='button' class='btn' data-toggle='modal' onclick=" + comment_function + ">Comment</a>"
        html_string += img_tag + "<br>" + button_tag+"<br>" + c_string + "<br>" + "<br>" + text_area
    # resp = HTTPResponse(body=html_string,status0=200)
    return html_string

#### It will allow the current user to view his/her image as well as other user images
@app.route('/viewall')
@login_required
def viewall():
    html_string=""
    posts=imgcoll.find()
    print posts
    for post in posts:
        print post
    for post in imgcoll.find():
        img1 = post['image_data']
        comments = post['comments']
        c_string = "<div><h5>Comments on Image </h5>"
        for comment in comments:
            c_string += "user:" + comment['username'] + "<br>" + "comment:" + comment['comment'] + "<br>"
        c_string += "</div>"
        decode = img1.decode()
        img_tag = '<img alt="sample" src="data:image/jpeg;base64,{0}">'.format(decode)
        post_id = "'" + post['post_id'] + "'"
        #button_tag = "<button onclick=\"deleteimage(" + post_id + ")\" class='btn'>Delete Image</button>"
        text_area = "<form action=\"/comment/" + post[
            'post_id'] + "\" method=\"post\"><input type=\"textarea\" maxlength=\"250\" name=\"comm\"><input type=\"submit\" value=\"post\"></form>"
        html_string += img_tag + "<br>" + "<br>" + c_string + "<br>" + "<br>" + text_area
    # resp = HTTPResponse(body=html_string,status0=200)
    return html_string

#### function to delete the comment of the user
@app.route('/deletecomment/<postid>/<commid>',methods=['POST','GET'])
def comment_delete(postid,commid):
    print "inside delete commment"
    #given_dic = imgcoll.find_one({"post_id":postid})
    output=imgcoll.update({'post_id' : postid},{"$pull" : {'comments':{'comm_id':commid}}})
    return redirect(url_for('view'))

#### Function to delete the image of the user
@app.route('/delete/<postid>',methods=['POST','GET'])
def delete(postid):
    delete_post_dict = {}
    username=session['username']
    delete_post_dict["username"] = username
    delete_post_dict["post_id"] = postid
    output = imgcoll.remove(delete_post_dict)
    msg = usercoll.update({'username': username}, {"$inc": {'limit': -1}})
    return redirect(url_for('view'))

### Function to post a comment for the image
@app.route("/comment/<postid>",methods=['POST','GET'])
@login_required
def up(postid):
    given_dic = imgcoll.find_one({"post_id": postid})
    comment = request.form['comm']
    userid=session['username']
    time=str(datetime.now())
    comment_dic = {}
    comment_dic['comm_id']=str(uuid.uuid1())
    comment_dic["comment"] = comment
    comment_dic["username"] = userid
    comment_dic["comment_time"] = str(datetime.now())
    given_dic['comments'].append(comment_dic)
    output = imgcoll.update({"post_id": postid}, given_dic)
    return redirect(url_for('view'))


@app.route('/upload')
@login_required
def upp():
    return render_template('upload.html')

#### Upload a image to the database
@app.route('/uploadimage',methods=['GET','POST'])
@login_required
def useruploadimage():
    if request.method == 'POST':
        file = request.files['image']
        image_data = file.read()
        size=len(image_data)
        kbytes=size/1024
        if kbytes>=1024:
            flash('File size too big')
            print "file is big"
            return render_template("upload.html")
        filen=file.filename
        filen=filen.split('.')
        try:
            if filen[1]:
                pass
        except Exception as e:
            flash('Only Image files allowed')
            return render_template("upload.html")
        if filen[1]=="jpg" or filen[1]=="png" or filen[1]=="jpeg":
            user_name = session['username']
            post_id = str(uuid.uuid1())
            get_details = usercoll.find_one({'username': user_name})
            print get_details['limit']
            get_limit = int(get_details['limit'])
            if get_limit < 10:
                output = insert_image(user_name, post_id, image_data)
                msg = usercoll.update({'username': user_name}, {"$inc": {'limit': 1}})
                return  redirect(url_for('view'))
            else:
                flash("User no of images limit exceeded")
                return render_template('menu.html')
        else:
            flash('Only Image files allowed')
            return render_template("upload.html")



def insert_image(username, post_id, image_data):
    post_dict = {}
    post_dict['username'] = username
    post_dict['post_id'] = post_id
    encoded_string = base64.b64encode(image_data)
    post_dict['image_data'] = encoded_string
    post_dict['post_time'] = str(datetime.now())
    post_dict['comments'] = []
    print 'in insert before insert'
    output = imgcoll.insert_one(post_dict)
    print 'in insert after insert'
    return output


def get_details_by_username(username):
    posts = []
    for post in imgcoll.find({"username": username}):
        posts.append(post)
    return posts


if __name__ == '__main__':
    app.run()
