#!/usr/bin/env python3
import boto3
import csv
from datetime import datetime

iam = boto3.client('iam')

def list_all_users():
    users = []
    paginator = iam.get_paginator('list_users')
    for page in paginator.paginate():
        for u in page['Users']:
            users.append(u['UserName'])
    return users

def list_access_keys(user):
    response = iam.list_access_keys(UserName=user)
    return response.get('AccessKeyMetadata', [])

def get_last_used(access_key_id):
    resp = iam.get_access_key_last_used(AccessKeyId=access_key_id)
    data = resp.get('AccessKeyLastUsed', {})
    return data.get('ServiceName'), data.get('LastUsedDate')

def main():
    output_file = 'iam_access_keys_report.csv'
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['UserName', 'AccessKeyId', 'Description', 'Status', 'CreateDate', 'LastUsedService', 'LastUsedDate']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for user in list_all_users():
            keys = list_access_keys(user)
            for k in keys:
                service, last_used_date = get_last_used(k['AccessKeyId'])
                writer.writerow({
                    'UserName': user,
                    'AccessKeyId': k['AccessKeyId'],
                    'Description': k.get('Description', ''),
                    'Status': k['Status'],
                    'CreateDate': k['CreateDate'].isoformat(),
                    'LastUsedService': service or '',
                    'LastUsedDate': last_used_date.isoformat() if last_used_date else ''
                })

    print(f"Report saved to {output_file}")

if __name__ == "__main__":
    main()
