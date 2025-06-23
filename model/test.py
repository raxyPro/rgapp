from sqlalchemy import create_engine

# Replace with your actual MySQL credentials and database name
username = 'rax'
password = '512'
host = 'localhost'
port = 3306
database = '`stockdata`'

# SQLAlchemy connection string
connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"

# Create the engine
engine = create_engine(connection_string)

# Test the connection
with engine.connect() as connection:
    result = connection.execute("SELECT VERSION()")
    version = result.fetchone()
    print(f"MySQL version: {version[0]}")