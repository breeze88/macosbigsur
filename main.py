import psycopg2
from AirTagCrypto import *
import requests
from datetime import datetime
from config import *
from hashlib import md5
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])

try:

    # PostgreSQL database connection details
    DB_HOST = 'localhost'
    DB_NAME = 'myair_development'
    DB_USER = 'postgres'
    DB_PASSWORD = 'Proposal5454@5454'

    # Connect to the database
    conn = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()

    # Process data
    tags = {}
    for key in private_keys:
        tag = AirTagCrypto(key)
        tags[tag.get_advertisement_key()] = tag

    data = requests.post(simple_server_url, json={"ids": list(tags.keys())}).json()

    if 'results' not in data:
        logging.warning('No results found')
    else:
        for result in data['results']:
            decrypt = tags[result['id']].decrypt_message(result['payload'])
            date_time = datetime.fromtimestamp(decrypt['timestamp'])

            logging.info(f'Processing result {result["id"]}')

            # Insert data into PostgreSQL
            if len(result['id']) > 33:
                sql = '''INSERT INTO songs (report_id, latitude, longitude, report_time, hash)
                         VALUES (%s, %s, %s, %s, %s)
                         ON CONFLICT (hash) DO NOTHING;'''
                values = (result['id'], decrypt['lat'], decrypt['lon'], date_time, md5((str(result['id']) + str(decrypt['lat']) + str(decrypt['lon'])).encode()).hexdigest())
                cursor.execute(sql, values)

            logging.debug(f'Result {result["id"]} processed')

    # Commit changes and close connection
    conn.commit()
    cursor.close()
    conn.close()

    logging.info('Data has been written to PostgreSQL')

except psycopg2.errors.ForeignKeyViolation as e:
    # Handle the ForeignKeyViolation exception here
    logging.exception(f'Error occurred: {e}')
    conn.rollback()
    cursor.close()
    conn.close()
    logging.warning('Insert failed due to foreign key constraint violation. Rolling back transaction.')

except Exception as e:
    # Handle any other exception
    logging.exception(f'Error occurred: {e}')
    raise
