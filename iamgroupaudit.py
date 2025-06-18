import boto3
import csv

def fetch_iam_group_data():
    iam = boto3.client('iam')
    groups_data = []

    paginator = iam.get_paginator('list_groups')
    for page in paginator.paginate():
        for group in page['Groups']:
            group_name = group['GroupName']

            # Managed policies attached to group
            attached_resp = iam.list_attached_group_policies(GroupName=group_name)
            managed_policies = [p['PolicyName'] for p in attached_resp.get('AttachedPolicies', [])]

            # Inline policies attached to group
            inline_resp = iam.list_group_policies(GroupName=group_name)
            inline_policies = inline_resp.get('PolicyNames', [])

            groups_data.append([
                group_name,
                ', '.join(managed_policies) if managed_policies else "None",
                ', '.join(inline_policies) if inline_policies else "None"
            ])
    return groups_data


if __name__ == '__main__':
    output_file = "iam_groups_report.csv"
    headers = [
        "Group Name",
        "Managed Policies",
        "Inline Policies"
    ]

    group_data = fetch_iam_group_data()

    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(group_data)

    print(f"✅ CSV file '{output_file}' has been created with IAM group policy details.")
