#!/usr/bin/env python3
import boto3
import csv

# Initialize IAM client
iam_client = boto3.client('iam')

# Define CSV file name
output_filename = "iam_users.csv"

# Define the CSV header
header = ["User", "Use Type", "Last console access", "Groups", "Directly Attached policies"]

# Function to get the use type
def get_use_type(username):
    try:
        iam_client.get_login_profile(UserName=username)
        return "Console"
    except iam_client.exceptions.NoSuchEntityException:
        return "Programmatic"

# Function to get last console access
def get_last_console_access(user):
    return user.get("PasswordLastUsed", "Never")

# Function to get group memberships
def get_user_groups(username):
    try:
        response = iam_client.list_groups_for_user(UserName=username)
        groups = [group["GroupName"] for group in response.get("Groups", [])]
        return ", ".join(groups) if groups else "Nil"
    except Exception:
        return "Nil"

# Function to get directly attached policies
def get_attached_policies(username):
    try:
        attached_policies = []
        response = iam_client.list_attached_user_policies(UserName=username)
        for policy in response.get("AttachedPolicies", []):
            attached_policies.append(policy["PolicyName"])
        
        inline_policies = iam_client.list_user_policies(UserName=username).get("PolicyNames", [])
        attached_policies.extend(inline_policies)
        
        return ", ".join(attached_policies) if attached_policies else "Nil"
    except Exception:
        return "Nil"

# Retrieve IAM users and compile data
rows = []
paginator = iam_client.get_paginator('list_users')
for page in paginator.paginate():
    for user in page["Users"]:
        username = user["UserName"]
        row = [
            username,
            get_use_type(username),
            get_last_console_access(user),
            get_user_groups(username),
            get_attached_policies(username)
        ]
        rows.append(row)

# Write to CSV file
with open(output_filename, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(header)
    writer.writerows(rows)

print(f"CSV file '{output_filename}' has been successfully created!")
