import os
import subprocess
import socket
import smtplib
from email.message import EmailMessage
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()
email_address = os.getenv("EMAIL")
app_password = os.getenv("APP_PASSWORD")
to_address = os.getenv("TO_ADDRESS")

now = datetime.datetime.now()
current_time = now.strftime('%Y-%m-%d %H:%M:%S')
current_time_2 = datetime.datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S')
current_time_converted = now.strftime('%I:%M:%S %p')
log_file = os.sys.path[0]
list_of_services = []
log_lines = 0

class Service:

    def __init__(self, name, address, port):
        self.name = name
        self.address = address
        self.port = port
        self.current_status = ''
        self.previous_status = ''
        self.last_time_online = datetime.datetime.fromtimestamp(0)
        self.last_time_offline = datetime.datetime.fromtimestamp(0)
        list_of_services.append(self)

"""
Define Services here to be monitored

var_name = Service('service name', 'service address', port number)

Example:

my_website = Service('My Website', 'example.com', 443)

"""

google = Service('Google', 'google.com', 443)
apple = Service('Apple', 'apple.com', 443)

def ping(host):

    command = ['ping', '-c', '3', '-W', '1', host]
    status = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if status.returncode == 0:
        return 'online'
    else:
        return 'offline'


def port_status(service_address, port):

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((service_address, port))
        sock.close()
        if result == 0:
            return 'online'
        else:
            return 'offline'
    except OSError:
        return 'offline'

def html_status(address, port):

    try:
        r = requests.head('https://' + address + ':' + str(port))
        if r.status_code == 200 or r.status_code == 302:
            return 'online'
        else:
            return 'offline'
    except requests.ConnectionError:
        return 'offline'

def send_email(subject, body):

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_address
    msg["To"] = to_address
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(email_address, app_password)
        smtp.send_message(msg)


def check_log_file(log_file):

    if os.path.isfile(log_file) == False:
        open(log_file, 'x').close()


def populate_obj_attributes(log_file, list_of_services):

    file = open(log_file, 'r')
    lines = file.readlines()
    global log_lines
    
    for service in list_of_services:

        if service.port == 'self':
            service.current_status = ping(service.address)
        else:
            if service.port == 443 or service.port == 8443:
                service.current_status = html_status(service.address, service.port)
            else:
                service.current_status = port_status(service.address, service.port)
            
        for line in lines:
            delimited_line = line.strip().split(';')
            address = delimited_line[0]
            log_service = delimited_line[1]
            status = delimited_line[2]
            log_time = delimited_line[3]
            log_lines += 1

            time = datetime.datetime.strptime(log_time, '%Y-%m-%d %H:%M:%S')

            if address == service.address and log_service == service.name:
                if status == 'offline':
                    service.last_time_offline = time
                elif status == 'online':
                    service.last_time_online = time

        if service.last_time_offline > service.last_time_online:
            service.previous_status = 'offline'
            if service.current_status == 'online':
                open(log_file, 'a').write(service.address + ';' + service.name + ';' + service.current_status + ';' + current_time + '\n')
                service.last_time_online = current_time_2
        elif service.last_time_online > service.last_time_offline:
            service.previous_status = 'online'
            if service.current_status == 'offline':
                open(log_file, 'a').write(service.address + ';' + service.name + ';' + service.current_status + ';' + current_time + '\n')
                service.last_time_offline = current_time_2
        elif service.current_status != service.previous_status:
            open(log_file, 'a').write(service.address + ';' + service.name + ';' + service.current_status + ';' + current_time + '\n')
    
    file.close()


def send_notification(list_of_services):

    for service in list_of_services:
        service_name = service.name.replace('_', ' ').title()
        service_last_time_offline_converted = datetime.datetime.strftime(service.last_time_offline, '%I:%M:%S %p')
        if service.current_status == 'online' and service.previous_status == 'offline':
            send_email(service_name + ' is back online', f'{service_name} came online at {current_time_converted}' + '\n' + f'{service_name} went offline at {service_last_time_offline_converted}.')
        elif service.current_status == 'offline' and service.previous_status == 'online':
            send_email(service_name + ' is offline!', f'{service_name} went offline at {service_last_time_offline_converted}.')
        elif service.current_status == 'offline' and service.previous_status == 'offline':
            time_offline = (now - service.last_time_offline)
            time_offline_minutes = int((time_offline.total_seconds())/60)
            if (time_offline_minutes >= 30 and time_offline_minutes % 30 == 0):
                if current_time_2 == service.last_time_offline + datetime.timedelta(minutes = time_offline_minutes):
                    send_email(service_name + ' is offline!', f'{service_name} went offline at {service_last_time_offline_converted}.' + '\n' + f'{service_name} has been offline for {time_offline_minutes} minutes.')
            elif (time_offline_minutes % 5 == 0 and time_offline_minutes != 0 and time_offline_minutes < 30):
                if current_time_2 == service.last_time_offline + datetime.timedelta(minutes = time_offline_minutes):
                    send_email(service_name + ' is offline!', f'{service_name} went offline at {service_last_time_offline_converted}.' + '\n' + f'{service_name} has been offline for {time_offline_minutes} minutes.')
                

def cleanup_log_file(file, lines):

    lines = lines/len(list_of_services)
    if lines > 200:
        subprocess.run(['sed', '-i', '-e', '1,100d', file])

if __name__ == "__main__":
    check_log_file(log_file)
    populate_obj_attributes(log_file, list_of_services)
    send_notification(list_of_services)
    cleanup_log_file(log_file, log_lines)
