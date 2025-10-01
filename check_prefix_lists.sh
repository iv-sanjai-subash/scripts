#!/bin/bash
# Read-only script to check if prefix list IDs exist in the AWS account across all regions

# File containing prefix list IDs (one per line)
INPUT_FILE="prefix_ids.txt"

# Get your AWS account ID (for filtering customer-owned lists)
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

# Loop through each prefix list ID in the file
while IFS= read -r PLID || [ -n "$PLID" ]; do
  echo "🔎 Checking prefix list ID: $PLID"

  # Loop through all regions
  for region in $(aws ec2 describe-regions --query "Regions[].RegionName" --output text); do
    # Describe prefix list in the region, filter for matches
    output=$(aws ec2 describe-managed-prefix-lists \
      --region "$region" \
      --prefix-list-ids "$PLID" \
      --query "PrefixLists[].{Region:'$region',ID:PrefixListId,Name:PrefixListName,Owner:OwnerId}" \
      --output table 2>/dev/null)

    # Print output if found
    [ -n "$output" ] && echo "$output"
  done
done < "$INPUT_FILE"
