#!/bin/bash
# Read-only script to check prefix list IDs across all regions
# Outputs exactly like AWS Console (both AWS-managed and customer-managed)

INPUT_FILE="prefix_ids.txt"

while IFS= read -r PLID || [ -n "$PLID" ]; do
  echo "🔎 Checking prefix list ID: $PLID"

  for region in $(aws ec2 describe-regions --query "Regions[].RegionName" --output text); do
    output=$(aws ec2 describe-managed-prefix-lists \
      --region "$region" \
      --prefix-list-ids "$PLID" \
      --query "PrefixLists[].{Region:'$region',ID:PrefixListId,Name:PrefixListName,Owner:OwnerId}" \
      --output table 2>/dev/null)

    [ -n "$output" ] && echo "$output"
  done
done < "$INPUT_FILE"
