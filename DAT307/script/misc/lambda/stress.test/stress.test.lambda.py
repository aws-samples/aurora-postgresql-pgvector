import json
import boto3
import psycopg2
from concurrent.futures import ThreadPoolExecutor
import os
import time
import subprocess
import optparse
import requests

def get_db_credentials(secret_name, region_name='us-west-2'):
    """Retrieve database credentials from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name=region_name)
    secret_value = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(secret_value['SecretString'])
    return secret['username'], secret['password'], secret['host'], secret.get('dbname', 'postgres')

def cpu_stress_test(cursor, duration_seconds):
    """Simulate CPU workload by running a compute-intensive query"""
    query = "SELECT COUNT(1) FROM cpustresstest a, cpustresstest b, cpustresstest c;"
    start_time = time.time()
    while time.time() - start_time < duration_seconds:
        cursor.execute(query)

def io_stress_test(cursor, duration_seconds):
    """Simulate CPU workload by running a io-intensive query"""
    query = "SELECT COUNT(1) FROM iostresstest a;"
    start_time = time.time()
    while time.time() - start_time < duration_seconds:
        cursor.execute(query)

def conn_stress_test(cursor, duration_seconds):
    """Simulate CPU workload by running a conn-intensive query"""
    query = "SELECT 1;"
    start_time = time.time()
    while time.time() - start_time < duration_seconds:
        cursor.execute(query)

def run_stress_test_in_thread(secret_name, workload_type, region_name, duration_seconds):
    """Function to be run in multiple threads"""
    username, password, host, dbname = get_db_credentials(secret_name, region_name)
    connection = psycopg2.connect(
        host=host,
        user=username,
        password=password,
        dbname=dbname
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("set statement_timeout = '{}s'".format(duration_seconds))
            if workload_type == 'CPU':
                cpu_stress_test(cursor, duration_seconds)
            elif workload_type == 'IO':
                io_stress_test(cursor, duration_seconds)
            elif workload_type == 'CONN':
                conn_stress_test(cursor, duration_seconds)
    finally:
        connection.close()

def lambda_handler(event, context):
    secret_name = event['secret_name']
    workload_type = event['workload_type']
    duration_seconds = event.get('duration_seconds', 60)  # Default duration: 60 seconds
    num_threads = event.get('num_threads', os.cpu_count() * 8)  # Default threads: 2x CPUs
    region_name = event.get('region_name', 'us-west-2')

    username, password, host, dbname = get_db_credentials(secret_name, region_name)
    
    if workload_type == 'CPU':
        with psycopg2.connect( host=host, user=username, password=password, dbname=dbname) as connection:
            with connection.cursor() as cursor:
                cursor.execute("drop table if exists cpustresstest;")
                cursor.execute("create table if not exists cpustresstest(id bigint primary key, col2 text);")
                cursor.execute("select count(1) from cpustresstest;")
                res = cursor.fetchone()
                print (res)
                if int(res[0]) <= 0:
                    cursor.execute("insert into cpustresstest select r, 'test '||r from generate_series(1, 100) r;")
                    cursor.execute("analyze cpustresstest;")
                    connection.commit()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(run_stress_test_in_thread, secret_name, workload_type, region_name, duration_seconds)
                for _ in range(num_threads)
            ]
            for future in futures:
                future.result()  # Wait for all threads to complete
    elif workload_type == 'IO':
        # pgbench -U postgres -i -s 20000 postgres -h rdspg1.cv2iwqsmwf4q.us-west-2.rds.amazonaws.com -U postgres -d postgres -p 5432
        # pgbench -U postgres -c 265 -j 65 -T 6000 -S postgres -p 5436
        os.environ['PGPASSWORD'] = password
        p = subprocess.Popen("/usr/bin/pgbench -i -s 2000 -h {} -U postgres -d postgres -p 5432".format(host), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in p.stdout.readlines():
            print (line)
        retval = p.wait()
        print (retval)
        p = subprocess.Popen("/usr/bin/pgbench -c 265 -j 65 -T {} -h {} -U postgres -d postgres -p 5432".format(duration_seconds, host), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in p.stdout.readlines():
            print (line)
        retval = p.wait()        
        print (retval)
    elif workload_type == 'CONN':
        with psycopg2.connect( host=host, user=username, password=password, dbname=dbname) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select setting from pg_settings where name = 'max_connections'")
                res = cursor.fetchone()
                num_threads = int(res[0] )
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(run_stress_test_in_thread, secret_name, workload_type, region_name, duration_seconds)
                for _ in range(num_threads)
            ]
            for future in futures:
                future.result()  # Wait for all threads to complete
    elif workload_type == "OOM":
       with psycopg2.connect( host=host, user=username, password=password, dbname=dbname) as connection:
           with connection.cursor() as cursor:
               cursor.execute("SELECT *,pg_sleep(1) FROM (SELECT *,repeat('x',99999) FROM generate_series(1,1000000) ORDER BY 1 OFFSET 1) a LIMIT 1")
    else:
        raise ValueError(f"Unsupported workload type: {workload_type}. Only 'CPU' is supported for this function.")
    
    return {
        'statusCode': 200,
        'body': json.dumps('{} stress test completed successfully'.format(workload_type))
    }

def parse_input():
    parser = optparse.OptionParser()
    parser.add_option('-s','--secret',
           dest='secret',
           default=None,
           action='store',
           type="str",
           metavar='secret',
           help='Secret Name for Database Credentials')
    parser.add_option('-w','--workload',
           dest='workload',
           action='store',
           type="choice",
           choices = ["CPU", "IO", "CONN", "OOM"],
           default="CPU",
           metavar='workload',
           help='Workload Test Type [CPU, IO, CONN, OOM]')
    parser.add_option('-t','--duration',
           dest='duration',
           action='store',
           type="int",
           default=600,
           metavar='duration',
           help='Test run duration (seconds)')
    (options, args) = parser.parse_args()
    return options

def get_region():

    headers = {'X-aws-ec2-metadata-token-ttl-seconds': '21600', 'content-type': 'application/json'}
    r = requests.put("http://169.254.169.254/latest/api/token", headers=headers)
    headers = {'X-aws-ec2-metadata-token': r.text}
    r = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document", headers=headers)
    return r.json().get('region')

if __name__=="__main__":
    options = parse_input()
    event = {}
    event['secret_name'] = options.secret
    event['workload_type'] = options.workload
    event['duration_seconds'] = options.duration
    event['region_name'] = get_region()
    lambda_handler(event, {})

# python3 ./stress.test.lambda.py -s rdspg-pgvector-secret -w IO -t 600
