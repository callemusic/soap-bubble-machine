# Deploy Updated Server to Pi

## Quick Deploy (Copy & Paste)

Run these commands in your terminal:

```bash
# 1. Copy the updated server file
scp server_py2.py pi@192.168.2.108:~/server.py

# 2. SSH to Pi and restart server
ssh pi@192.168.2.108 "pkill -f 'python.*server.py'; sleep 1; cd ~ && nohup python server.py > server.log 2>&1 &"
```

You'll be prompted for your Pi password twice (once for scp, once for ssh).

## Or Use Web GUI

If your current Pi server already has the `/upload_server` endpoint:
1. Open your web GUI
2. Click the purple "Deploy Server" button
3. Select `server_py2.py`
4. SSH to Pi and restart: `ssh pi@192.168.2.108 "pkill -f 'python.*server.py'; python server.py"`

## Verify Deployment

After deploying, test the connection:
```bash
curl http://192.168.2.108:8080/health
```

You should see the motor positions in the response.

