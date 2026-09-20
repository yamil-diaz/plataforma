import psycopg2

for pwd in ['postgres', 'admin', 'password', '123456', '']:
    try:
        conn = psycopg2.connect(host='localhost', database='plataforma_dev', user='postgres', password=pwd)
        print('Connected with password:', repr(pwd))
        conn.close()
        break
    except Exception as e:
        print('Password', repr(pwd), 'failed:', e)