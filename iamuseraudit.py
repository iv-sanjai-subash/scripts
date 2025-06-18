import boto3
import csv

def get_iam_details():
    """Retrieve read-only IAM details without modifications."""
    iam_client = boto3.client('iam')
    users_data = []

    # Use paginator to go through all IAM users.
    paginator = iam_client.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            username = user['UserName']

            # Retrieve groups the user belongs to.
            groups_resp = iam_client.list_groups_for_user(UserName=username)
            groups = ', '.join([group['GroupName'] for group in groups_resp.get('Groups', [])])

            # Retrieve AWS managed policies attached to the user.
            attached_policies_resp = iam_client.list_attached_user_policies(UserName=username)
            aws_managed = ', '.join([policy['PolicyName'] for policy in attached_policies_resp.get('AttachedPolicies', [])])

            # Retrieve inline (custom) policies attached to the user.
            inline_policies_resp = iam_client.list_user_policies(UserName=username)
            custom_policies = ', '.join(inline_policies_resp.get('PolicyNames', []))

            # Retrieve access keys and details about their last used information.
            access_keys_resp = iam_client.list_access_keys(UserName=username)
            access_keys_info = []
            for key in access_keys_resp.get('AccessKeyMetadata', []):
                key_id = key['AccessKeyId']
                last_used_resp = iam_client.get_access_key_last_used(AccessKeyId=key_id)
                last_used = last_used_resp.get('AccessKeyLastUsed', {})
                service = last_used.get('ServiceName', 'N/A')
                last_used_date = last_used.get('LastUsedDate', 'N/A')
                access_keys_info.append(f"{key_id} (Last Used: {service} on {last_used_date})")
            access_keys_str = " | ".join(access_keys_info)

            # Append aggregated data for the user.
            users_data.append([
                username,
                groups if groups else "None",
                aws_managed if aws_managed else "None",
                custom_policies if custom_policies else "None",
                access_keys_str if access_keys_str else "None"
            ])
    return users_data

if __name__ == '__main__':
    iam_details = get_iam_details()
    filename = 'iam_details.csv'
    headers = ["UserName", "Groups", "AWS Managed Policies", "Custom Policies", "Access Keys (Last Used)"]

    # Write details to CSV file.
    with open(filename, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        writer.writerows(iam_details)

    print(f"CSV file '{filename}' has been created with the IAM audit details.")
