import boto3
import json

def get_policy_document(iam_client, policy_arn):
    try:
        policy = iam_client.get_policy(PolicyArn=policy_arn)
        version_id = policy['Policy']['DefaultVersionId']
        version = iam_client.get_policy_version(PolicyArn=policy_arn, VersionId=version_id)
        return version['PolicyVersion']['Document']
    except Exception as e:
        return {"error": str(e)}

def fetch_user_permissions_combined():
    iam_client = boto3.client('iam')
    output_lines = []

    users = iam_client.list_users()
    for user in users['Users']:
        username = user['UserName']
        output_lines.append(f"User:\n\n** {username}\n")

        aws_managed = set()
        customer_managed = {}

        # Directly attached user policies
        attached_policies = iam_client.list_attached_user_policies(UserName=username)
        for policy in attached_policies.get('AttachedPolicies', []):
            policy_arn = policy['PolicyArn']
            policy_name = policy['PolicyName']
            if policy_arn.startswith('arn:aws:iam::aws:policy/'):
                aws_managed.add(policy_name)
            else:
                policy_doc = get_policy_document(iam_client, policy_arn)
                customer_managed[policy_name] = policy_doc

        # Group policies
        groups_resp = iam_client.list_groups_for_user(UserName=username)
        for group in groups_resp.get('Groups', []):
            group_name = group['GroupName']
            group_policies = iam_client.list_attached_group_policies(GroupName=group_name)
            for policy in group_policies.get('AttachedPolicies', []):
                policy_arn = policy['PolicyArn']
                policy_name = policy['PolicyName']
                if policy_arn.startswith('arn:aws:iam::aws:policy/'):
                    aws_managed.add(policy_name)
                else:
                    policy_doc = get_policy_document(iam_client, policy_arn)
                    customer_managed[policy_name] = policy_doc

        # Output AWS Managed
        output_lines.append("\nAWS Managed:")
        output_lines += [f"\t{p}" for p in sorted(aws_managed)] if aws_managed else ["\tNone"]

        # Output Customer Managed with JSON
        output_lines.append("\n\nCustomer Managed:\n")
        if customer_managed:
            for name, doc in customer_managed.items():
                output_lines.append(f"{name} -- ")
                output_lines.append(json.dumps(doc, indent=4) + "\n")
        else:
            output_lines.append("None\n")

        output_lines.append("\n" + "-"*60 + "\n")

    return "\n".join(output_lines)

if __name__ == '__main__':
    result = fetch_user_permissions_combined()

    output_file = "iam_user_combined_permissions.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"\n✅ File '{output_file}' created successfully in your CloudShell directory.")
