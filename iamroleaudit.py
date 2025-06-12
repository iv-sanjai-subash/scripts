#!/usr/bin/env python3
import csv
import boto3
import botocore
import io
import json
import sys
import time
import urllib.parse

def get_account_id():
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    return identity['Account']

def get_credential_report():
    iam = boto3.client('iam')
    try:
        # Initiate generation of the credential report.
        response = iam.generate_credential_report()
        # Wait until the report is complete.
        while response['State'] != 'COMPLETE':
            time.sleep(2)
            response = iam.generate_credential_report()
        report = iam.get_credential_report()
        return report['Content'].decode('utf-8')
    except botocore.exceptions.ClientError as e:
        sys.stderr.write(f"Error generating credential report: {e}\n")
        sys.exit(1)

def parse_users(report_data):
    # Parse CSV data from the credential report.
    users = []
    csv_reader = csv.DictReader(io.StringIO(report_data))
    for row in csv_reader:
        users.append(row)
    return users

def fetch_roles():
    iam = boto3.client('iam')
    roles = []
    paginator = iam.get_paginator('list_roles')
    for page in paginator.paginate():
        roles.extend(page['Roles'])
    return roles

def get_latest_activity(user):
    """
    Determine the most recent activity for an IAM user.
    It checks both console login (password_last_used) and access key usage.
    """
    candidate_fields = []
    
    # Check for console login usage.
    if user['password_last_used'] != 'N/A':
        candidate_fields.append(user['password_last_used'])
    # Check access key 1 usage.
    if user.get('access_key_1_last_used_date', 'N/A') != 'N/A':
        candidate_fields.append(user['access_key_1_last_used_date'])
    # Check access key 2 usage.
    if user.get('access_key_2_last_used_date', 'N/A') != 'N/A':
        candidate_fields.append(user['access_key_2_last_used_date'])
    
    if candidate_fields:
        # ISO-8601 strings sort naturally.
        return max(candidate_fields)
    else:
        return ""

def get_trusted_entities(role):
    """
    Extracts and returns a comma-separated string of trusted entities
    from an IAM role's AssumeRolePolicyDocument.
    """
    doc = role.get("AssumeRolePolicyDocument", {})
    if isinstance(doc, str):
        try:
            # Sometimes the document might be URL-encoded.
            decoded_doc = urllib.parse.unquote(doc)
            doc = json.loads(decoded_doc)
        except Exception:
            try:
                doc = json.loads(doc)
            except Exception as e:
                return f"Error parsing policy: {e}"
    
    principals = []
    if 'Statement' in doc:
        statements = doc['Statement']
        if not isinstance(statements, list):
            statements = [statements]
        for stmt in statements:
            principal = stmt.get("Principal", {})
            if isinstance(principal, dict):
                for k, v in principal.items():
                    if isinstance(v, list):
                        principals.extend(v)
                    else:
                        principals.append(v)
            elif isinstance(principal, str):
                principals.append(principal)
    return ", ".join(principals)

def main():
    output_filename = 'audit_report.csv'
    
    account_id = get_account_id()
    
    report_data = get_credential_report()
    user_report = parse_users(report_data)
    
    # Updated header includes Trusted Entities as the last column.
    header = ['Name', 'Account', 'Type', 'Use Type', 'Last Activity', 'MFA Active', 'Trusted Entities']
    
    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        
        # Process IAM users from the credential report.
        for user in user_report:
            name = user['user']
            user_type = "User"
            # "Console" if password is enabled; otherwise assume API.
            use_type = "Console" if user['password_enabled'].lower() == 'true' else "API"
            last_activity = get_latest_activity(user)
            mfa_active = user['mfa_active']
            # For users, Trusted Entities is not applicable.
            trusted_entities = ""
            writer.writerow([name, account_id, user_type, use_type, last_activity, mfa_active, trusted_entities])
        
        # Process IAM roles.
        for role in fetch_roles():
            name = role['RoleName']
            user_type = "Role"
            use_type = "AssumedRole"
            # Roles do not have console activity.
            last_activity = ""
            mfa_active = "N/A"
            # Get trusted entities from the AssumeRolePolicyDocument.
            trusted_entities = get_trusted_entities(role)
            writer.writerow([name, account_id, user_type, use_type, last_activity, mfa_active, trusted_entities])
    
    print(f"CSV audit report generated: {output_filename}")

if __name__ == '__main__':
    main()
