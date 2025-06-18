import boto3
from tabulate import tabulate

def get_iam_details():
    """Retrieve read-only IAM details without modifications."""
    iam_client = boto3.client('iam')
    users_data = []

    # Iterate through all IAM users using paginator to cover many users.
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

            # Retrieve access keys and details about last used info.
            access_keys_resp = iam_client.list_access_keys(UserName=username)
            access_keys_info = []
            for key in access_keys_resp.get('AccessKeyMetadata', []):
                key_id = key['AccessKeyId']
                last_used_resp = iam_client.get_access_key_last_used(AccessKeyId=key_id)
                last_used = last_used_resp.get('AccessKeyLastUsed', {})
                service = last_used.get('ServiceName', 'N/A')
                last_used_date = last_used.get('LastUsedDate', 'N/A')
                access_keys_info.append(f"{key_id} (Last Used: {service} on {last_used_date})")
            access_keys_str = "\n".join(access_keys_info)

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
    headers = ["UserName", "Groups", "AWS Managed Policies", "Custom Policies", "Access Keys (Last Used)"]
    table = tabulate(iam_details, headers=headers, tablefmt="grid")
    print(table)
