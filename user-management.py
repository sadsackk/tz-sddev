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

#    for cell, value in header_data.items():
#        target_worksheet.update_acell(cell, value)

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
            f'I{num}': user_info['billing_status'],
        }

        for cell, value in cell_updates.items():
            target_worksheet.update_acell(cell, value)


def freeipa_user_handler(client, source_data, user_map):

    for row in source_data:
        id, firstname, lastname, email = row
        username = firstname.lower() + '.' + lastname[0].lower()
        try:
            new_user = client.user_show(username)
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
        status_info = client.user_status(username)['summary'].split(':')[1].strip()
        status = "Disabled" if status_info == "True" else "Enabled"
        username = new_user['result']['uid'][0]
        user_map[int(id)] = {"firstname": firstname, "lastname": lastname, "email": email, "username": username, "status": status}

    for row in source_data:
        row.append(f'{row[1]} {row[2]}')

    info = client.user_find()

    full_names = {item[-1] for item in source_data}

    api_display_names = {entry['displayname'][0] for entry in info['result'] if 'displayname' in entry}

    users_to_delete = api_display_names - full_names
    
    for user in users_to_delete:
        parts = user.split()
        username = f'{parts[0].lower()}.{parts[1].lower()[0]}'
        client.user_del(username)
        print(f'user {username} deleted')
        


def slack_user_handler(slack_bot_client, slack_user_client, user_map):
    slack_user_data = None
    slack_bill_data = None
    try:
        slack_user_data = slack_bot_client.users_list()
        slack_bill_data = slack_user_client.team_billableInfo()
    except SlackApiError as e:
        print(f"Произошла ошибка: {e.response['error']}")

    for user_id, user_info in user_map.items():
        username = user_info['username']
        slack_member = next((user for user in slack_user_data['members'] if user['name'] == username), None)
    
        if slack_member:
            user_info['slack_id'] = slack_member['id']
            user_info['slack_name'] = slack_member['real_name']

        billing_info = slack_bill_data.get(user_id, {})

        user_info['billing_status'] = billing_info.get('billing_active', "not billed")


        if 'slack_id' not in user_map[user_id]:
            user_info['slack_id'] = '-'
            user_info['slack_name'] = '-'
            user_info['billing_status'] = '-'    


def main():
    client = gspread.authorize(credentials)
    spreadsheet = client.open('umrellio test')
    worksheet = spreadsheet.worksheet('data')
    sh_data = worksheet.get_all_values()
    source_data = sh_data[1:]
    load_dotenv()
    slack_bot_client = WebClient(os.getenv("SLACK_BOT_TOKEN"))
    slack_user_client = WebClient(os.getenv("SLACK_USER_TOKEN"))
    ipa_client = ClientMeta('ipa.demo1.freeipa.org')
    ipa_client.login('admin', 'Secret123')
    user_map = {}

    freeipa_user_handler(ipa_client, source_data, user_map)
    #slack_user_handler(slack_bot_client, slack_user_client, user_map)

    #create_result_table(user_map)

if __name__ == "__main__":
    main()