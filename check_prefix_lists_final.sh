#!/bin/bash
# Read-only script to check prefix list IDs across all regions
# Outputs a table if found, or "Not found" if missing

INPUT_FILE="prefix_ids.txt"

while IFS= read -r PLID || [ -n "$PLID" ]; do
  echo "🔎 Checking prefix list ID: $PLID"
  found_any=false

  for region in $(aws ec2 describe-regions --query "Regions[].RegionName" --output text); do
    output=$(aws ec2 describe-managed-prefix-lists \
      --region "$region" \
      --prefix-list-ids "$PLID" \
      --query "PrefixLists[].{Region:'$region',ID:PrefixListId,Name:PrefixListName,Owner:OwnerId}" \
      --output table 2>/dev/null)

    if [ -n "$output" ]; then
      echo "$output"
      found_any=true
    fi
  done

  if [ "$found_any" = false ]; then
    echo "❌ $PLID not found in any region"
  fi

  echo "---------------------------------------------"
done < "$INPUT_FILE"
