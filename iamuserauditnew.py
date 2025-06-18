import boto3
import csv

def get_iam_details():
    """Retrieve IAM details, including user groups, permissions policies (separated as AWS Managed and Customer Created), 
    and access key usage details. All calls are read-only."""
    iam_client = boto3.client('iam')
    users_data = []

    # Paginate through all IAM users.
    paginator = iam_client.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            username = user['UserName']

            # Fetch groups for the user.
            groups_resp = iam_client.list_groups_for_user(UserName=username)
            groups = ', '.join(group['GroupName'] for group in groups_resp.get('Groups', []))

            # First, fetch all attached policies.
            attached_resp = iam_client.list_attached_user_policies(UserName=username)
            aws_managed_policies = []      # Will store policies with AWS managed ARNs.
            customer_created_policies = [] # Will store all customer-managed policies.

            # Separate policies based on their ARN.
            for policy in attached_resp.get('AttachedPolicies', []):
                policy_arn = policy.get('PolicyArn', '')
                if policy_arn.startswith('arn:aws:iam::aws:policy/'):
                    aws_managed_policies.append(policy['PolicyName'])
                else:
                    customer_created_policies.append(policy['PolicyName'])

            # Next, fetch inline (customer-created) policies.
            inline_resp = iam_client.list_user_policies(UserName=username)
            inline_policies = inline_resp.get('PolicyNames', [])
            customer_created_policies.extend(inline_policies)

            # Retrieve and format access keys details.
            access_keys_resp = iam_client.list_access_keys(UserName=username)
            access_keys_list = []
            for key in access_keys_resp.get('AccessKeyMetadata', []):
                key_id = key.get('AccessKeyId')
                # Get last used information for each access key.
                last_used_info = iam_client.get_access_key_last_used(AccessKeyId=key_id).get('AccessKeyLastUsed', {})
                service_name = last_used_info.get('ServiceName', 'N/A')
                last_used_date = last_used_info.get('LastUsedDate', 'N/A')
                access_keys_list.append(f"{key_id} (Last Used: {service_name} on {last_used_date})")
            access_keys_str = " | ".join(access_keys_list) if access_keys_list else "None"

            # Append the row of aggregated data.
            users_data.append([
                username,
                groups if groups else "None",
                ', '.join(aws_managed_policies) if aws_managed_policies else "None",
                ', '.join(customer_created_policies) if customer_created_policies else "None",
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
        "Customer Created Policies", 
        "Access Keys (Last Used)"
    ]
    
    # Write the aggregated data to a CSV file.
    with open(filename, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        writer.writerows(iam_details)
        
    print(f"CSV file '{filename}' has been created with the IAM audit details.")
