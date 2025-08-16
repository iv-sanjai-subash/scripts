#!/usr/bin/env python3
"""
get_tomcat_info_csv_v2.py

Run from AWS CloudShell. Interactive selection of EC2 instance(s), sends a read-only
SSM Run Command to each selected instance to find Tomcat server.xml Connector ports,
maps listening processes, and writes CSV with header:

account ID,instance_name,public_ip,user,tomcat_home,serverxml_path,connector_port,redirect_port,domainwithporturl,proc_uid,proc_cmd

Notes:
- Script does NOT modify instances. It only runs read-only commands via SSM.
- Requires IAM permissions: ec2:DescribeInstances, ssm:SendCommand, ssm:GetCommandInvocation, sts:GetCallerIdentity.
"""

import boto3
import csv
import datetime
import sys
import time

# Shell script run on instance (read-only)
SSM_SCRIPT = r'''
#!/bin/bash
set -u

echo "SSM_TOMCAT_SCAN_START"
# find server.xml in common locations under /home, /opt, /srv, /var
find /home /opt /srv /var -type f -name server.xml 2>/dev/null | sort -u | while read -r f; do
  # only consider those under a conf/ path to reduce noise
  if echo "$f" | grep -q "/conf/server.xml"; then
    tomcat_home="$(dirname "$(dirname "$f")")"
    # guess user from /home/<user>/... otherwise empty
    user="$(echo "$f" | awk -F/ '{print $3}' 2>/dev/null || echo '')"
    # extract Connector tags
    grep -oP '<Connector[^>]*>' "$f" 2>/dev/null | while read -r conn; do
      port="$(echo "$conn" | sed -n 's/.*port="\([^"]*\)".*/\1/p' || true)"
      redirectPort="$(echo "$conn" | sed -n 's/.*redirectPort="\([^"]*\)".*/\1/p' || true)"
      # normalize empty
      [ -z "$port" ] && port=""
      [ -z "$redirectPort" ] && redirectPort=""
      echo "SERVERXML|$f|$tomcat_home|$user|$port|$redirectPort"
    done
  fi
done

# list listening sockets to map port -> pid -> uid -> cmd
ss -tulpen 2>/dev/null | awk 'NR>1 {print}' | while read -r line; do
  # find token with :port at end
  token=""
  for tok in $line; do
    if echo "$tok" | grep -qE ':[0-9]+$'; then
      token="$tok"
      break
    fi
  done
  port=""
  [ -n "$token" ] && port="$(echo "$token" | sed -E 's/.*:([0-9]+)$/\1/')"
  pid="$(echo "$line" | grep -oP 'pid=\K[0-9]+' || echo '')"
  uid="$(echo "$line" | awk '{print $3}' || echo '')"
  if [ -n "$pid" ] && [ -r "/proc/$pid/cmdline" ]; then
    cmd="$(tr '\0' ' ' < /proc/$pid/cmdline | sed -n 's/^[[:space:]]*//;s/[[:space:]]*$//p')"
  else
    cmd="$(echo "$line" | tr -s ' ' | cut -c1-200)"
  fi
  echo "LISTEN|$port|$pid|$uid|$cmd"
done

echo "SSM_TOMCAT_SCAN_END"
'''

def p(msg=""):
    print(msg)

def get_account_id(sts):
    resp = sts.get_caller_identity()
    return resp.get('Account', '')

def list_instances(ec2):
    resp = ec2.describe_instances(
        Filters=[{'Name':'instance-state-name','Values':['running','stopped','stopping','pending']}]
    )
    insts = []
    for r in resp.get('Reservations', []):
        for i in r.get('Instances', []):
            iid = i.get('InstanceId')
            name = ''
            for t in i.get('Tags', []):
                if t.get('Key','').lower() == 'name':
                    name = t.get('Value','')
            insts.append({
                'InstanceId': iid,
                'Name': name,
                'PrivateIp': i.get('PrivateIpAddress',''),
                'PublicIp': i.get('PublicIpAddress',''),
            })
    return insts

def choose_instances(instances):
    if not instances:
        p("No instances found.")
        sys.exit(1)
    p("Available instances:")
    for idx, inst in enumerate(instances, 1):
        p(f"{idx}. {inst['InstanceId']}  Name:{inst['Name'] or '-'}  PublicIP:{inst['PublicIp'] or '-'}  PrivateIP:{inst['PrivateIp'] or '-'}")
    p("\nEnter comma-separated numbers (e.g. 1 or 1,3). Press Enter to cancel.")
    sel = input("Selection: ").strip()
    if sel == "":
        p("Cancelled.")
        sys.exit(0)
    picked = []
    for part in sel.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
            if 1 <= n <= len(instances):
                picked.append(instances[n-1]['InstanceId'])
        except Exception:
            p(f"Ignoring invalid selection: {part}")
    if not picked:
        p("No valid instances selected. Exiting.")
        sys.exit(1)
    return list(dict.fromkeys(picked))

def send_ssm(ssm, instance_ids):
    resp = ssm.send_command(
        InstanceIds=instance_ids,
        DocumentName='AWS-RunShellScript',
        Parameters={'commands':[SSM_SCRIPT]},
        TimeoutSeconds=300,
    )
    return resp['Command']['CommandId']

def poll_result(ssm, iid, cmd_id, timeout=300, interval=3):
    elapsed = 0
    while True:
        try:
            out = ssm.get_command_invocation(CommandId=cmd_id, InstanceId=iid, PluginName='aws:RunShellScript')
        except ssm.exceptions.InvocationDoesNotExist:
            time.sleep(interval); elapsed += interval
            if elapsed > timeout:
                return {'Status':'TimedOut','Stdout':'','Stderr':'Timeout waiting for invocation'}
            continue
        status = out.get('Status','')
        if status in ('Pending','InProgress','Delayed'):
            time.sleep(interval); elapsed += interval
            if elapsed > timeout:
                return {'Status':'TimedOut','Stdout':out.get('StandardOutputContent',''),'Stderr':out.get('StandardErrorContent','')}
            continue
        return {'Status':status,'Stdout':out.get('StandardOutputContent',''),'Stderr':out.get('StandardErrorContent','')}

def parse_output(stdout):
    server_rows = []
    listen_map = {}
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("SERVERXML|"):
            # SERVERXML|serverxml_path|tomcat_home|user|port|redirectPort
            parts = line.split("|", 6)
            if len(parts) >= 6:
                _, serverxml_path, tomcat_home, user, port, redirectPort = parts[:6]
                server_rows.append({
                    'serverxml_path': serverxml_path,
                    'tomcat_home': tomcat_home,
                    'user': user,
                    'connector_port': port,
                    'redirect_port': redirectPort
                })
        elif line.startswith("LISTEN|"):
            # LISTEN|port|pid|uid|cmd
            parts = line.split("|", 5)
            if len(parts) >= 5:
                _, port, pid, uid, cmd = parts[:5]
                if port:
                    listen_map.setdefault(port, []).append({'pid':pid,'uid':uid,'cmd':cmd})
    # merge
    for r in server_rows:
        p = r.get('connector_port','')
        mappings = listen_map.get(p, [])
        if mappings:
            r['proc_pid'] = mappings[0].get('pid','')
            r['proc_uid'] = mappings[0].get('uid','')
            r['proc_cmd'] = mappings[0].get('cmd','')
        else:
            r['proc_pid'] = ''
            r['proc_uid'] = ''
            r['proc_cmd'] = ''
    return server_rows

def main():
    session = boto3.Session()
    ec2 = session.client('ec2')
    ssm = session.client('ssm')
    sts = session.client('sts')

    account_id = get_account_id(sts)
    p(f"AWS Account ID: {account_id}")

    instances = list_instances(ec2)
    picked_ids = choose_instances(instances)

    try:
        cmd_id = send_ssm(ssm, picked_ids)
    except Exception as e:
        p("Failed to send SSM command. Ensure ssm:SendCommand permission and managed instance status.")
        p(str(e))
        sys.exit(1)
    p(f"SSM Command ID: {cmd_id}")

    all_rows = []
    # collect and parse per-instance
    for iid in picked_ids:
        p(f"Waiting for results from {iid} ...")
        res = poll_result(ssm, iid, cmd_id, timeout=300, interval=3)
        p(f"Status for {iid}: {res['Status']}")
        if res.get('Stderr'):
            p(f"SSM stderr (first 300 chars): {res['Stderr'][:300]}")
        parsed = parse_output(res.get('Stdout',''))
        # add instance metadata
        meta = next((x for x in instances if x['InstanceId']==iid), {})
        for r in parsed:
            public_ip = meta.get('PublicIp','')
            private_ip = meta.get('PrivateIp','')
            port = r.get('connector_port','')
            domainwithporturl = ''
            if port:
                if public_ip:
                    domainwithporturl = f"{public_ip}:{port}"
                elif private_ip:
                    domainwithporturl = f"{private_ip}:{port}"
            all_rows.append({
                'account_id': account_id,
                'instance_name': meta.get('Name',''),
                'public_ip': public_ip,
                'user': r.get('user',''),
                'tomcat_home': r.get('tomcat_home',''),
                'serverxml_path': r.get('serverxml_path',''),
                'connector_port': port,
                'redirect_port': r.get('redirect_port',''),
                'domainwithporturl': domainwithporturl,
                'proc_uid': r.get('proc_uid',''),
                'proc_cmd': r.get('proc_cmd',''),
            })

    # write CSV with the exact header requested
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outname = f"tomcat_ports_{ts}.csv"
    headers = ['account ID','instance_name','public_ip','user','tomcat_home','serverxml_path','connector_port','redirect_port','domainwithporturl','proc_uid','proc_cmd']

    if all_rows:
        with open(outname, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            for r in all_rows:
                writer.writerow([
                    r.get('account_id',''),
                    r.get('instance_name',''),
                    r.get('public_ip',''),
                    r.get('user',''),
                    r.get('tomcat_home',''),
                    r.get('serverxml_path',''),
                    r.get('connector_port',''),
                    r.get('redirect_port',''),
                    r.get('domainwithporturl',''),
                    r.get('proc_uid',''),
                    r.get('proc_cmd',''),
                ])
        p(f"Wrote {len(all_rows)} rows to ~/{outname}")
    else:
        p("No rows discovered. No CSV written.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        p("\nInterrupted by user. Exiting.")
        sys.exit(1)
