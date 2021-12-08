from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'employee'


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('AddEmp.html')

@app.route("/about", methods=['GET','POST'])
def about():
    return render_template('GetEmp.html', about=about)

@app.route("/getemp", methods=['GET','POST'])
def GetEmp():
    return render_template('GetEmp.html', GetEmp=GetEmp)

def show_image(bucket):
    s3_client = boto3.client('s3')
    public_urls = []
    
    #check whether the emp_id inside the image_url
    emp_id = request.form['emp_id']

    try:
        for item in s3_client.list_objects(Bucket=bucket)['Contents']:
            presigned_url = s3_client.generate_presigned_url('get_object', Params = {'Bucket': bucket, 'Key': item['Key']}, ExpiresIn = 100)
            if emp_id in presigned_url:
               public_urls.append(presigned_url)
    except Exception as e:
        pass
    # print("[INFO] : The contents inside show_image = ", public_urls)
    return public_urls

# @app.route('/fetchdata/<emp_id>')
@app.route("/fetchdata", methods=['GET','POST'])
def fetchdata():
    if request.method == 'POST':
        try:
            emp_id = request.form['emp_id']
            cursor = db_conn.cursor()
            # fetch_emp_sql = "SELECT emp_id AS Id, first_name AS fname, last_name AS lname FROM employee WHERE emp_id = %s"
            fetch_emp_sql = "SELECT * FROM employee WHERE emp_id = %s"
            cursor.execute(fetch_emp_sql,(emp_id))
            emp_id= cursor.fetchall()  
            
            (id,fname,lname,priSkill,location) = emp_id[0]
            image_url = show_image(custombucket)

            return render_template('GetEmpOutput.html', id=id,fname=fname,lname=lname,priSkill=priSkill,location=location,image_url=image_url)
        except Exception as e:
            return render_template('IdNotFound.html')
    else:
        return render_template('AddEmp.html', fetchdata=fetchdata)

@app.route('/delete-emp', methods=['GET','POST'])
def DeleteEmp(bucket):
    emp_id= request.form['emp_id']
    mycursor = db_conn.cursor()
    del_emp_sql = "DELETE FROM employee WHERE emp_id = %s"
    mycursor.execute(del_emp_sql, (emp_id))
    db_conn.commit()
    

    s3_client = boto3.client('s3')
    emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
    try:
        s3_client.delete_object(Bucket=bucket, Key = emp_image_file_name_in_s3)    
        return render_template('SuccessDelete.html')
    except Exception as e:
        return render_template('UnsuccessDelete.html')


    # return render_template('SuccessDelete.html')


@app.route("/addemp", methods=['GET','POST'])
def AddEmp():
    if request.method == 'POST':
        emp_id = request.form['emp_id']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        pri_skill = request.form['pri_skill']
        location = request.form['location']
        emp_image_file = request.files['emp_image_file']

        insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
        cursor = db_conn.cursor()

        if emp_image_file.filename == "":
            return "Please select a file"

        try:

            cursor.execute(insert_sql, (emp_id, first_name, last_name, pri_skill, location))
            db_conn.commit()
            emp_name = "" + first_name + " " + last_name
            # Uplaod image file in S3 #
            emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
            s3 = boto3.resource('s3')

            try:
                print("Data inserted in MySQL RDS... uploading image to S3...")
                s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
                bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                s3_location = (bucket_location['LocationConstraint'])

                if s3_location is None:
                    s3_location = ''
                else:
                    s3_location = '-' + s3_location

                object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                    s3_location,
                    custombucket,
                    emp_image_file_name_in_s3)

            except Exception as e:
                return str(e)

        finally:
            cursor.close()

        print("all modification done...")
        return render_template('AddEmpOutput.html', name=emp_name)
    else:
        return render_template('GetEmp.html', AddEmp=AddEmp)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
