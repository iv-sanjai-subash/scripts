import boto3
import csv

def get_iam_details():
    iam_client = boto3.client('iam')
    users_data = []

    paginator = iam_client.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            username = user['UserName']

            # Groups and their attached policies
            groups_resp = iam_client.list_groups_for_user(UserName=username)
            groups = [g['GroupName'] for g in groups_resp.get('Groups', [])]

            group_aws_policies = []
            group_customer_policies = []

            for group_name in groups:
                attached_group_policies = iam_client.list_attached_group_policies(GroupName=group_name)
                for policy in attached_group_policies.get('AttachedPolicies', []):
                    if policy['PolicyArn'].startswith('arn:aws:iam::aws:policy/'):
                        group_aws_policies.append(policy['PolicyName'])
                    else:
                        group_customer_policies.append(policy['PolicyName'])

                # Add inline group policies
                inline_group_policies = iam_client.list_group_policies(GroupName=group_name)
                group_customer_policies.extend(inline_group_policies.get('PolicyNames', []))

            # Direct attached user policies
            attached_user_policies = iam_client.list_attached_user_policies(UserName=username)
            user_aws_policies = []
            user_customer_policies = []

            for policy in attached_user_policies.get('AttachedPolicies', []):
                if policy['PolicyArn'].startswith('arn:aws:iam::aws:policy/'):
                    user_aws_policies.append(policy['PolicyName'])
                else:
                    user_customer_policies.append(policy['PolicyName'])

            # Inline user policies
            inline_user_policies = iam_client.list_user_policies(UserName=username)
            user_customer_policies.extend(inline_user_policies.get('PolicyNames', []))

            # Access keys
            access_keys_resp = iam_client.list_access_keys(UserName=username)
            access_keys = []
            for key in access_keys_resp.get('AccessKeyMetadata', []):
                key_id = key.get('AccessKeyId')
                last_used_info = iam_client.get_access_key_last_used(AccessKeyId=key_id).get('AccessKeyLastUsed', {})
                service = last_used_info.get('ServiceName', 'N/A')
                last_used = last_used_info.get('LastUsedDate', 'N/A')
                access_keys.append(f"{key_id} (Used: {service} on {last_used})")
            access_keys_str = " | ".join(access_keys) if access_keys else "None"

            users_data.append([
                username,
                ", ".join(groups) if groups else "None",
                ", ".join(user_aws_policies + group_aws_policies) if (user_aws_policies or group_aws_policies) else "None",
                ", ".join(user_customer_policies + group_customer_policies) if (user_customer_policies or group_customer_policies) else "None",
                access_keys_str
            ])
    return users_data

if __name__ == '__main__':
    iam_details = get_iam_details()
    headers = [
        "UserName", 
        "Groups", 
        "AWS Managed Policies (User + Group)", 
        "Customer Created Policies (User + Group)", 
        "Access Keys (Last Used)"
    ]

    with open('iam_details.csv', mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(iam_details)

    print("CSV file 'iam_details.csv' created with IAM audit details.")
