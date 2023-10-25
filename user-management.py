import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from python_freeipa import ClientMeta
from python_freeipa import exceptions

json_keyfile = 'umrellio-test-82e357d92ba9.json'
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)

def create_result_table(user_map):
    client = gspread.authorize(credentials)

    target_spreadsheet = client.open('test2')
    target_worksheet = target_spreadsheet.get_worksheet(0)

    header_data = {
        'A1': 'ID',
        'B1': 'First Name',
        'C1': 'Last Name',
        'D1': 'E-mail',
        'E1': 'FreeIPA login',
        'F1': 'FreeIPA status',
        'G1': 'Slack Member ID',
        'H1': 'Slack Full Name',
        'I1': 'Slack Billing status'
    }

    for cell, value in header_data.items():
        target_worksheet.update_acell(cell, value)

    for id, user_info in user_map.items():
        num = int(id) + 1

        cell_updates = {
            f'A{num}': id,
            f'B{num}': user_info['firstname'],
            f'C{num}': user_info['lastname'],
            f'D{num}': user_info['email'],
            f'E{num}': user_info['username'],
            f'F{num}': user_info['status'],
            f'G{num}': user_info['slack_name'],
            f'H{num}': user_info['slack_id'],
            f'I{num}': user_info['billing_active'],
        }

        for cell, value in cell_updates.items():
            target_worksheet.update_acell(cell, value)

def slack_info():
    
    load_dotenv()

    client = WebClient(os.getenv("SLACK_BOT_TOKEN"))
    client2 = WebClient(os.getenv("SLACK_USER_TOKEN"))

    try:
        data = client.users_list()
        bill_data = client2.team_billableInfo()

    
    except SlackApiError as e:
        print(f"Произошла ошибка: {e.response['error']}")

    updated_user_map = user_map.copy()

    for user_id, user_info in updated_user_map.items():
        username = user_info['username']
        data_user_info = next((user for user in data['members'] if user['name'] == username), None)

        if data_user_info:
            user_info['slack_id'] = data_user_info['id'] 
            user_info['slack_name'] = data_user_info['real_name'] 

        billing_info = bill_data.get(user_id, {})

        user_info['billing_active'] = 'active' if billing_info.get('billing_active', False) else 'not active'

def main():
    client = gspread.authorize(credentials)

    spreadsheet = client.open('umrellio test')
    worksheet = spreadsheet.worksheet('data')

    data = worksheet.get_all_values()
    data = data[1:]
    client = ClientMeta('ipa.demo1.freeipa.org')
    client.login('admin', 'Secret123')

    for row in data:
        id, firstname, lastname, email = row
        username = firstname.lower() + '.' + lastname[0].lower()

        try:
            user = client.user_show(username)
            print(f"user {username} already exists")
        except exceptions.NotFound:
            client.user_add(username, firstname, lastname, email)
            print(f"created user {username}")
        
        if int(id) in [3, 5]: 
            try:
                client.user_disable(username)
                print(f"user {username} status set to disable")
            except exceptions.AlreadyInactive:
                print(f"user {username} is already disabled")
        




    #create_result_table(updated_user_map)

if __name__ == "__main__":
    main()
