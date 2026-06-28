import os
import time
import pymysql
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# Read DB connection details from environment variables (with fallback for local dev)
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 8625))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'dkjp6d93')
DB_NAME = os.environ.get('DB_NAME', 'cki101_db')

def get_db_connection(max_retries=5, delay=2):
    """
    Attempt to connect to the database with a retry mechanism.
    This helps the application survive container startup latency.
    """
    retries = 0
    while retries < max_retries:
        try:
            return pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                cursorclass=pymysql.cursors.DictCursor
            )
        except pymysql.MySQLError as e:
            retries += 1
            print(f"Database connection failed ({DB_HOST}:{DB_PORT}). Retry {retries}/{max_retries} in {delay}s... Error: {e}")
            time.sleep(delay)
    # Raise the last error if all retries failed
    raise Exception(f"Could not connect to database at {DB_HOST}:{DB_PORT} after {max_retries} attempts.")

def init_db():
    """
    Initialize the database table and insert default data if the table is empty.
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Create users table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    age INT NOT NULL
                )
            ''')
            
            # Check if table is empty
            cursor.execute("SELECT COUNT(*) as count FROM users")
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute("INSERT INTO users (name, age) VALUES (%s, %s)", ('張三', 25))
                cursor.execute("INSERT INTO users (name, age) VALUES (%s, %s)", ('李四', 30))
                connection.commit()
                print("Database initialized with default users.")
            else:
                print("Database table already exists and contains data.")
        connection.close()
    except Exception as e:
        print(f"Database initialization error: {e}")

@app.route('/')
def index():
    # As requested by initial prompt: Visiting / should return plain text "我是功能一"
    return "我是功能一"

@app.route('/user')
def user_page():
    # Serve user management webpage at /user
    return render_template('index.html')

@app.route('/api/user', methods=['GET', 'POST', 'DELETE'])
def handle_user_api():
    if request.method == 'DELETE':
        # Delete user by name
        name = request.args.get('name')
        if not name:
            data = request.get_json(silent=True) or {}
            name = data.get('name')
            
        if not name:
            return jsonify({"error": "Missing name"}), 400
            
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                sql = "DELETE FROM users WHERE name = %s"
                cursor.execute(sql, (name,))
                connection.commit()
            connection.close()
            return jsonify({
                "message": "User deleted successfully",
                "name": name
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == 'POST':
        # Add new user
        data = request.get_json(silent=True) or request.form
        name = data.get('name')
        age = data.get('age')
        
        if not name or age is None:
            return jsonify({"error": "Missing name or age"}), 400
            
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                sql = "INSERT INTO users (name, age) VALUES (%s, %s)"
                cursor.execute(sql, (name, int(age)))
                connection.commit()
            connection.close()
            return jsonify({
                "message": "User created successfully", 
                "user": {"name": name, "age": int(age)}
            }), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    # GET method (Query user(s))
    name_query = request.args.get('name')
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            if name_query:
                # Query specific user by name
                sql = "SELECT name, age FROM users WHERE name = %s"
                cursor.execute(sql, (name_query,))
            else:
                # Query all users
                sql = "SELECT name, age FROM users"
                cursor.execute(sql)
            result = cursor.fetchall()
        connection.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GCP Storage Section ---

@app.route('/gcp')
def gcp_page():
    # Serve GCP Cloud Storage bucket browser page
    return render_template('gcp.html')

@app.route('/api/gcp/buckets')
def list_gcp_buckets():
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({"error": "Missing project_id parameter"}), 400
        
    try:
        from google.cloud import storage
        # Initialize storage client using specified project ID (uses ADC automatically)
        client = storage.Client(project=project_id)
        buckets = client.list_buckets()
        
        bucket_list = []
        for bucket in buckets:
            bucket_list.append({
                "name": bucket.name,
                "location": bucket.location,
                "storage_class": bucket.storage_class,
                "time_created": bucket.time_created.isoformat() if bucket.time_created else None
            })
        return jsonify(bucket_list), 200
    except Exception as e:
        error_msg = str(e)
        print(f"GCS listing error: {error_msg}")
        return jsonify({"error": error_msg}), 500

if __name__ == '__main__':
    # Initialize the database on startup
    init_db()
    # Running on 0.0.0.0 is required for Docker containers to be accessible externally
    app.run(host='0.0.0.0', port=5000)
