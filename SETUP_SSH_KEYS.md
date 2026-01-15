# SSH Key Setup for Passwordless Access

## Option 1: Add Key During Imager Setup (Easiest)

1. **In Raspberry Pi Imager SSH settings:**
   - Enable SSH ✅
   - Select **"Use public key authentication"**
   - Click "Add public key"
   - Copy and paste your public key (shown below)

2. **Your public key:**
   ```
   [Copy the key from terminal output]
   ```

3. **Flash and boot** - You'll be able to SSH without password!

## Option 2: Add Key After First Login

If you already flashed with password auth:

1. **First login with password:**
   ```bash
   ssh pi@192.168.2.108
   # Enter password
   ```

2. **Add your public key:**
   ```bash
   # On your Mac, run:
   ssh-copy-id pi@192.168.2.108
   # Enter password one last time
   ```

3. **Test passwordless login:**
   ```bash
   ssh pi@192.168.2.108
   # Should work without password!
   ```

## Your Public Key Location

Your main SSH key is at: `~/.ssh/id_ed25519.pub`

To view it:
```bash
cat ~/.ssh/id_ed25519.pub
```
