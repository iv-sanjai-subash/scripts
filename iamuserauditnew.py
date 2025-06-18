import boto3
import csv

def get_iam_details():
    """Retrieve read-only IAM details and separate AWS managed vs custom policies."""
    iam_client = boto3.client('iam')
    users_data = []

    # Paginator to handle a large number of users.
    paginator = iam_client.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            username = user['UserName']

            # Get groups associated with the user.
            groups_resp = iam_client.list_groups_for_user(UserName=username)
            groups = ', '.join([group['GroupName'] for group in groups_resp.get('Groups', [])])
            
            # Retrieve attached policies and separate them.
            attached_policies_resp = iam_client.list_attached_user_policies(UserName=username)
            aws_managed_policies = []  # for AWS managed policies
            custom_managed_policies = []  # for customer-managed (attached) policies
            for policy in attached_policies_resp.get('AttachedPolicies', []):
                policy_arn = policy['PolicyArn']
                if policy_arn.startswith('arn:aws:iam::aws:policy/'):
                    aws_managed_policies.append(policy['PolicyName'])
                else:
                    custom_managed_policies.append(policy['PolicyName'])
            
            # Retrieve inline policies.
            inline_policies_resp = iam_client.list_user_policies(UserName=username)
            inline_policies = inline_policies_resp.get('PolicyNames', [])
            
            # Combine custom managed attached policies and inline policies.
            custom_policies = custom_managed_policies + inline_policies

            # Retrieve access key details. Format each key's info.
            access_keys_resp = iam_client.list_access_keys(UserName=username)
            access_keys_info = []
            for key in access_keys_resp.get('AccessKeyMetadata', []):
                key_id = key['AccessKeyId']
                last_used_resp = iam_client.get_access_key_last_used(AccessKeyId=key_id)
                last_used_data = last_used_resp.get('AccessKeyLastUsed', {})
                service = last_used_data.get('ServiceName', 'N/A')
                last_used_date = last_used_data.get('LastUsedDate', 'N/A')
                access_keys_info.append(f"{key_id} (Last Used: {service} on {last_used_date})")
            access_keys_str = " | ".join(access_keys_info) if access_keys_info else "None"

            # Append aggregated data for the user.
            users_data.append([
                username,
                groups if groups else "None",
                ', '.join(aws_managed_policies) if aws_managed_policies else "None",
                ', '.join(custom_policies) if custom_policies else "None",
                access_keys_str
            ])
    return users_data

if __name__ == '__main__':
    iam_details = get_iam_details()
    filename = 'iam_details.csv'
    headers = [
        "UserName", 
        "Groups", 
        "AWS Managed Policies", 
        "Custom Policies (Attached & Inline)", 
        "Access Keys (Last Used)"
    ]
    
    with open(filename, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        writer.writerows(iam_details)
        
    print(f"CSV file '{filename}' has been created with the IAM audit details.")
