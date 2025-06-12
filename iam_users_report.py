import boto3
import csv
from datetime import datetime

iam = boto3.client('iam')

csv_file = 'iam_identity_audit.csv'

def format_datetime(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ') if dt else ''

def get_user_info(user):
    user_name = user['UserName']
    try:
        user_detail = iam.get_user(UserName=user_name)['User']
    except Exception:
        user_detail = {}
    last_console = user_detail.get('PasswordLastUsed')
    use_type = 'Console' if last_console else 'Programmatic'
    last_console = format_datetime(last_console) if last_console else 'Never'

    groups = iam.list_groups_for_user(UserName=user_name)['Groups']
    group_names = [g['GroupName'] for g in groups]
    group_str = '\n'.join(group_names) if group_names else 'Nil'

    attached_policies = iam.list_attached_user_policies(UserName=user_name)['AttachedPolicies']
    policy_names = [p['PolicyName'] for p in attached_policies]
    policy_str = '\n'.join(policy_names) if policy_names else 'Nil'

    mfa = iam.list_mfa_devices(UserName=user_name)
    mfa_active = 'TRUE' if mfa['MFADevices'] else 'FALSE'

    keys = iam.list_access_keys(UserName=user_name)['AccessKeyMetadata']
    if keys:
        key = keys[0]
        key_active = 'TRUE' if key['Status'] == 'Active' else 'FALSE'
        key_rotated = format_datetime(key['CreateDate'])

        key_last_used = iam.get_access_key_last_used(AccessKeyId=key['AccessKeyId'])
        used_info = key_last_used.get('AccessKeyLastUsed', {})
        last_used_date = format_datetime(used_info.get('LastUsedDate'))
        last_used_region = used_info.get('Region', '')
        last_used_service = used_info.get('ServiceName', '')
    else:
        key_active = 'FALSE'
        key_rotated = ''
        last_used_date = ''
        last_used_region = ''
        last_used_service = ''

    return [
        user_name, 'Prod', use_type, last_console,
        group_str, policy_str, mfa_active,
        key_active, key_rotated, last_used_date, last_used_region, last_used_service
    ]

def get_role_info(role):
    role_name = role['RoleName']
    create_date = format_datetime(role['CreateDate'])
    attached_policies = iam.list_attached_role_policies(RoleName=role_name)['AttachedPolicies']
    policy_names = [p['PolicyName'] for p in attached_policies]
    policy_str = '\n'.join(policy_names) if policy_names else 'Nil'

    return [
        role_name, 'Prod', 'Role', 'N/A',
        'Nil', policy_str, 'N/A',
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A'
    ]

# Write CSV
with open(csv_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow([
        'User', 'Account', 'Use Type', 'Last console access',
        'Groups', 'Directly Attached', 'mfa_active',
        'access_key_1_active', 'access_key_1_last_rotated',
        'access_key_1_last_used_date', 'access_key_1_last_used_region',
        'access_key_1_last_used_service'
    ])

    # Add IAM Users
    users = iam.list_users()['Users']
    for user in users:
        row = get_user_info(user)
        writer.writerow(row)

    # Add IAM Roles
    roles = iam.list_roles()['Roles']
    for role in roles:
        row = get_role_info(role)
        writer.writerow(row)

print(f"✅ IAM identity audit complete. Output saved to: {csv_file}")
