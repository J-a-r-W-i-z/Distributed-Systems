import mysql.connector

# Establish connection to MySQL server
connection = mysql.connector.connect(
    host='localhost',
    database='stud_test',
    user='root',
    password='password'
)

# Check if the connection is successful
if connection.is_connected():
    print("Connected to MySQL database")
else:
    print("Failed to connect to MySQL database")

# You can now perform operations on the database using this connection

# Don't forget to close the connection when you're done
connection.close()
