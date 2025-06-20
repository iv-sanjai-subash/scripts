import boto3
import csv

def get_iam_user_details():
    iam = boto3.client('iam')
    users_data = []

    paginator = iam.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            username = user['UserName']

            # --- Groups Attached to the User ---
            groups_resp = iam.list_groups_for_user(UserName=username)
            group_names = [g['GroupName'] for g in groups_resp.get('Groups', [])]

            # --- Directly Attached Policies (Managed + Inline) ---
            # Managed
            attached_policies_resp = iam.list_attached_user_policies(UserName=username)
            direct_managed = [p['PolicyName'] for p in attached_policies_resp.get('AttachedPolicies', [])]

            # Inline
            inline_policies_resp = iam.list_user_policies(UserName=username)
            direct_inline = inline_policies_resp.get('PolicyNames', [])

            direct_policies = direct_managed + direct_inline

            # --- Group Policies (Managed + Inline) ---
            group_policies = []
            for group in group_names:
                # Managed group policies
                group_attached_resp = iam.list_attached_group_policies(GroupName=group)
                group_managed = [p['PolicyName'] for p in group_attached_resp.get('AttachedPolicies', [])]

                # Inline group policies
                group_inline_resp = iam.list_group_policies(GroupName=group)
                group_inline = group_inline_resp.get('PolicyNames', [])

                group_policies.extend(group_managed + group_inline)

            # --- All Effective Policies ---
            all_policies = direct_policies + group_policies

            users_data.append([
                username,
                ", ".join(group_names) if group_names else "None",
                ", ".join(all_policies) if all_policies else "None",
                ", ".join(direct_policies) if direct_policies else "None",
                ", ".join(group_policies) if group_policies else "None"
            ])
    
    return users_data


if __name__ == '__main__':
    output_file = "iam_user_policy_report.csv"
    headers = [
        "Username",
        "Attached Groups",
        "All Policies (Direct + Group)",
        "Directly Attached Policies",
        "Group Policies Only"
    ]

    data = get_iam_user_details()

    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)

    print(f"\n✅ CSV file '{output_file}' created successfully in the current CloudShell directory.")
