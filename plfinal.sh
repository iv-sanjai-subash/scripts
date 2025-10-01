#!/bin/bash
# Read-only script: only shows prefix lists visible in AWS Console

INPUT_FILE="prefix_ids.txt"

while IFS= read -r PLID || [ -n "$PLID" ]; do
  echo "🔎 Checking prefix list ID: $PLID"
  found_any=false

  for region in $(aws ec2 describe-regions --query "Regions[].RegionName" --output text); do
    output=$(aws ec2 describe-managed-prefix-lists \
      --region "$region" \
      --output table 2>/dev/null | grep "$PLID")

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
