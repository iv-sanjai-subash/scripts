#!/bin/bash
# Read-only script to check customer-managed prefix lists across all regions
# Skips AWS-managed PLs automatically

INPUT_FILE="prefix_ids.txt"
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

while IFS= read -r PLID || [ -n "$PLID" ]; do
  echo "🔎 Checking prefix list ID: $PLID"
  found_any=false

  for region in $(aws ec2 describe-regions --query "Regions[].RegionName" --output text); do
    result=$(aws ec2 describe-managed-prefix-lists \
      --region "$region" \
      --prefix-list-ids "$PLID" \
      --query "PrefixLists[?OwnerId=='$ACCOUNT_ID'].{ID:PrefixListId,Name:PrefixListName}" \
      --output table 2>/dev/null)

    if [ -n "$result" ]; then
      echo "$result"
      found_any=true
    fi
  done

  if [ "$found_any" = false ]; then
    echo "❌ $PLID not found as customer-managed in any region"
  fi

  echo "---------------------------------------------"
done < "$INPUT_FILE"
