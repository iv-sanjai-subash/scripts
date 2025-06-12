import boto3
import csv
from datetime import datetime

iam = boto3.client('iam')

def get_console_access(user):
    try:
        response = iam.get_user(UserName=user)
        last_access = response.get('User', {}).get('PasswordLastUsed')
        return last_access.strftime('%Y-%m-%dT%H:%M:%SZ') if last_access else 'Never'
    except:
        return 'Never'

def get_groups(user):
    response = iam.list_groups_for_user(UserName=user)
    groups = [g['GroupName'] for g in response['Groups']]
    return '\n'.join(groups) if groups else 'Nil'

def get_attached_policies(user):
    response = iam.list_attached_user_policies(UserName=user)
    policies = [p['PolicyName'] for p in response['AttachedPolicies']]
    return '\n'.join(policies) if policies else 'Nil'

def get_mfa_status(user):
    response = iam.list_mfa_devices(UserName=user)
    return 'TRUE' if response['MFADevices'] else 'FALSE'

def get_access_key_details(user):
    keys = iam.list_access_keys(UserName=user)['AccessKeyMetadata']
    if not keys:
        return ['FALSE', '', '', '', '', '']
    key_id = keys[0]['AccessKeyId']
    active = str(keys[0]['Status'] == 'Active')
    rotated = keys[0]['CreateDate'].strftime('%Y-%m-%dT%H:%M:%SZ')

    last_used = iam.get_access_key_last_used(AccessKeyId=key_id)
    used_info = last_used.get('AccessKeyLastUsed', {})
    used_date = used_info.get('LastUsedDate')
    used_date_fmt = used_date.strftime('%Y-%m-%dT%H:%M:%SZ') if used_date else ''
    region = used_info.get('Region', '')
    service = used_info.get('ServiceName', '')

    return [active, rotated, used_date_fmt, region, service]

# Output CSV file path
csv_file = 'iam_user_audit.csv'

with open(csv_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    # Header
    writer.writerow([
        'User', 'Account', 'Use Type', 'Last console access',
        'Groups', 'Directly Attached', 'mfa_active',
        'access_key_1_active', 'access_key_1_last_rotated',
        'access_key_1_last_used_date', 'access_key_1_last_used_region',
        'access_key_1_last_used_service'
    ])

    users = iam.list_users()['Users']
    for u in users:
        user_name = u['UserName']
        account = 'Prod'  # You can change or automate this if needed
        use_type = 'Programmatic'  # Default assumption
        last_console = get_console_access(user_name)
        if last_console != 'Never':
            use_type = 'Console'  # Console access means both may be enabled

        groups = get_groups(user_name)
        policies = get_attached_policies(user_name)
        mfa = get_mfa_status(user_name)
        access_details = get_access_key_details(user_name)

        writer.writerow([
            user_name, account, use_type, last_console,
            groups, policies, mfa,
            access_details[0], access_details[1],
            access_details[2], access_details[3], access_details[4]
        ])

print(f"✅ Audit completed. Output saved to: {csv_file}")
