#!/usr/bin/env python3
import csv
import boto3
import botocore
import io
import sys
import time

def get_account_id():
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    return identity['Account']

def get_credential_report():
    iam = boto3.client('iam')
    # Initiate the generation of the credential report.
    try:
        response = iam.generate_credential_report()
        # Wait until the report is complete.
        while response['State'] != 'COMPLETE':
            time.sleep(2)  # Wait before checking again.
            response = iam.generate_credential_report()
        report = iam.get_credential_report()
        # The content is returned as a bytes object.
        return report['Content'].decode('utf-8')
    except botocore.exceptions.ClientError as e:
        sys.stderr.write("Error generating credential report: {}\n".format(e))
        sys.exit(1)

def parse_users(report_data):
    # Read CSV data from the credential report.
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

def main():
    # Define the output CSV file name in the script.
    output_filename = 'audit_report.csv'
    
    # Get the AWS Account ID.
    account_id = get_account_id()
    
    # Retrieve and parse the credential report.
    report_data = get_credential_report()
    user_report = parse_users(report_data)
    
    # Setup CSV header.
    header = ['Name', 'Account', 'Type', 'Use Type', 'Last Console Access', 'MFA Active']
    
    # Open the CSV file to write the output.
    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        
        # Process IAM users from the credential report.
        # "Use Type" is based on whether the password is enabled.
        for user in user_report:
            name = user['user']
            user_type = "User"
            use_type = "Console" if user['password_enabled'].lower() == 'true' else "API"
            last_console_access = user['password_last_used'] if user['password_last_used'] != 'N/A' else ""
            mfa_active = user['mfa_active']
            writer.writerow([name, account_id, user_type, use_type, last_console_access, mfa_active])
        
        # Process IAM roles.
        for role in fetch_roles():
            name = role['RoleName']
            user_type = "Role"
            use_type = "AssumedRole"
            last_console_access = ""  # Roles do not have console login.
            mfa_active = "N/A"
            writer.writerow([name, account_id, user_type, use_type, last_console_access, mfa_active])
    
    print(f"CSV report generated: {output_filename}")

if __name__ == '__main__':
    main()
