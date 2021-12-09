from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *
from datetime import datetime

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
    return render_template('AboutUs.html', about=about)

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


@app.route("/fetchdata", methods=['GET','POST'])
def fetchdata():
    if request.method == 'POST':
        try:
            emp_id = request.form['emp_id']
            cursor = db_conn.cursor()

            fetch_emp_sql = "SELECT * FROM employee WHERE emp_id = %s"
            cursor.execute(fetch_emp_sql,(emp_id))
            emp= cursor.fetchall()  
            
            (id,fname,lname,priSkill,location) = emp[0]
            image_url = show_image(custombucket)

            return render_template('GetEmpOutput.html', id=id,fname=fname,lname=lname,priSkill=priSkill,location=location,image_url=image_url)
        except Exception as e:
            return render_template('IdNotFound.html')
    else:
        return render_template('AddEmp.html', fetchdata=fetchdata)

@app.route('/delete-emp', methods=['GET','POST'])
def DeleteEmp():
    emp_id= request.form['emp_id']
    
    mycursor = db_conn.cursor()
    del_att_sql = "DELETE FROM attendance WHERE emp_id = %s"
    mycursor.execute(del_att_sql, (emp_id))
    db_conn.commit()


    mycursor = db_conn.cursor()
    del_emp_sql = "DELETE FROM employee WHERE emp_id = %s"
    mycursor.execute(del_emp_sql, (emp_id))
    db_conn.commit()
    

    s3_client = boto3.client('s3')
    emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
    try:
        s3_client.delete_object(Bucket=custombucket, Key = emp_image_file_name_in_s3)    
        return render_template('SuccessDelete.html')
    except Exception as e:
        return render_template('UnsuccessDelete.html')

@app.route('/view-attendance', methods=['GET','POST'])
def ViewAttendance():
    att_emp_sql = "SELECT * FROM attendance"
    cursor = db_conn.cursor()
    cursor.execute(att_emp_sql)
    att_result= cursor.fetchall()  
    return render_template('ViewAttendance.html', att_result=att_result)
        


        
    


@app.route('/attendance-emp', methods=['GET','POST'])
def AttendanceEmp():
    if request.method == 'POST':

        # datetime object containing current date and time
        now = datetime.now()
        dt_string = now.strftime("%d%m%Y%H%M%S")
        d_string = now.strftime("%d/%m/%Y")
        t_string = now.strftime("%H:%M:%S")

        attendance_id = request.form['attendance_id'] + dt_string
        date = request.form['date'] + d_string
        time = request.form['time'] + t_string
        attendance = request.form.getlist('attendance')
        emp_id = request.form['emp_id']

        # cursor = db_conn.cursor(db_conn.cursors.DictCursor)
        
        attendance = ','.join(attendance)
        att_values = (attendance)

        try:

            insert_att_sql = 'INSERT INTO attendance VALUES (%s,%s,%s,%s,%s)'
            cursor = db_conn.cursor()

            cursor.execute(insert_att_sql, (attendance_id,date,time,att_values,emp_id))
            db_conn.commit()

            return render_template('SuccessTakeAttendance.html', Id = attendance_id )
        except Exception as e:
                return str(e)

        finally:
            cursor.close()

    



@app.route("/addemp", methods=['GET','POST'])
def AddEmp():
    if request.method == 'POST':

        # datetime object containing current date and time
        now = datetime.now()
        dt_string = now.strftime("%d%m%Y%H%M%S")

        emp_id = request.form['emp_id'] + dt_string
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
        return render_template('AddEmpOutput.html', name=emp_name, id=emp_id)
    else:
        return render_template('GetEmp.html', AddEmp=AddEmp)

@app.route("/editemp", methods=['GET','POST'])
def EditEmp():
    if request.method == 'POST':
        
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        pri_skill = request.form['pri_skill']
        location = request.form['location']
        emp_id = request.form['emp_id']
        emp_image_file = request.files['emp_image_file']

        update_sql = "UPDATE employee SET first_name = %s, last_name = %s, pri_skill = %s, location = %s WHERE emp_id = %s"
        cursor = db_conn.cursor()

        changefield = (first_name, last_name, pri_skill, location, emp_id)

        try:
            cursor.execute(update_sql, (changefield))
            db_conn.commit()
            emp_name = "" + first_name + " " + last_name

            #if user upload new image 
            if emp_image_file.filename == "":
                print("select nothing")
            
            else:
                # Delete previous version of image in s3 then upload the new one (avoid of mutiple version store in s3)
                s3_client = boto3.client('s3')
                emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
                s3_client.delete_object(Bucket=custombucket, Key = emp_image_file_name_in_s3) 

                # Uplaod image file in S3 #
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
        return render_template('SuccessUpdate.html', name=emp_name,id=emp_id)
    else:
        return render_template('GetEmp.html', AddEmp=AddEmp)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
