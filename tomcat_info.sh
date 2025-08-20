#!/bin/bash
# Read-only Tomcat User Audit Script
# Collects: username, tomcat home directory, redirect port, status

OUTPUT="tomcat_users.csv"
echo "Username,Tomcat_Home,Redirect_Port,Status" > "$OUTPUT"

# Loop through users in /home
for userdir in /home/*; do
    [ -d "$userdir" ] || continue
    username=$(basename "$userdir")

    # Find all server.xml under this user, pick the latest modified one
    latest_serverxml=$(find "$userdir" -type f -name "server.xml" 2>/dev/null \
        -printf '%T@ %p\n' | sort -nr | head -n1 | awk '{print $2}')

    if [ -z "$latest_serverxml" ]; then
        echo "$username,,," >> "$OUTPUT"
        continue
    fi

    tomcat_home=$(dirname "$(dirname "$latest_serverxml")")

    # Extract redirect port (unique port used by domain in browser)
    redirect_port=$(grep -oP 'redirectPort="\K[0-9]+' "$latest_serverxml" | head -n1)

    if [ -z "$redirect_port" ]; then
        echo "$username,$tomcat_home,," >> "$OUTPUT"
        continue
    fi

    # Check if the port is active/listening
    if ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":$redirect_port$"; then
        status="Active"
    else
        status="Stopped"
    fi

    echo "$username,$tomcat_home,$redirect_port,$status" >> "$OUTPUT"
done
