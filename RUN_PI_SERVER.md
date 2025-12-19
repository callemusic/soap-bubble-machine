# Running the Pi Server

## Quick Start

### Option 1: Deploy Automatically (if SSH is set up)
```bash
./deploy-simple.sh
```

### Option 2: Manual SSH and Run
```bash
# SSH to Pi
ssh pi@192.168.2.108

# On the Pi, navigate to your directory and run:
python server.py

# Or run in background:
nohup python server.py > server.log 2>&1 &
```

### Option 3: Set up SSH first, then deploy
```bash
# Set up SSH key (enter password once)
./setup-ssh-key.sh

# Then deploy
./deploy-simple.sh
```

## Server Details

- **File**: `server_py2.py` (Python 2, uses raw sockets)
- **Port**: 8080
- **Endpoints**:
  - `GET /health` - Health check
  - `POST /set_state` - Set machine state (IDLE, DIP, OPEN, BLOW, CLOSE)
  - `POST /update_config` - Update configuration

## Check if Server is Running

```bash
# SSH to Pi
ssh pi@192.168.2.108

# Check if server is running
ps aux | grep server.py

# View logs (if running in background)
tail -f server.log

# Test health endpoint
curl http://192.168.2.108:8080/health
```

## Stop Server

```bash
# SSH to Pi
ssh pi@192.168.2.108

# Kill the server
pkill -f 'python.*server.py'
```

