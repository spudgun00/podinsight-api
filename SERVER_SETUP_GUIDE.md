# PodInsightHQ Dashboard - Server Setup Guide

This guide provides comprehensive instructions for running the Next.js development server, including troubleshooting common issues.

## Quick Start

```bash
# Navigate to project directory
cd /Users/jamesgill/PodInsights/podinsight-dashboard

# Start the development server
npm run dev
```

The server will be available at: **http://localhost:3000**

## Server Startup Scripts

We've created helper scripts to ensure reliable server startup:

### Option 1: Use the start-dev.sh script
```bash
./start-dev.sh
```
This script automatically:
- Checks for processes on port 3000
- Kills any blocking processes
- Starts the Next.js dev server

### Option 2: Use the run-dev.js script
```bash
node run-dev.js
```
This provides:
- Health monitoring
- Real-time server status
- Automatic health checks

## Common Issues & Solutions

### Issue: "Port 3000 is already in use"

**Solution 1: Kill the process using port 3000**
```bash
# Find what's using port 3000
lsof -i :3000

# Kill the process (replace PID with actual process ID)
kill -9 <PID>

# Or kill all processes on port 3000
lsof -ti :3000 | xargs kill -9
```

**Solution 2: Use the cleanup script**
```bash
./start-dev.sh
```

### Issue: "Connection Refused" errors

**Possible Causes:**
1. Server hasn't fully started yet (wait 3-5 seconds)
2. Server crashed silently
3. Firewall blocking localhost

**Solutions:**
```bash
# Check if server is actually running
ps aux | grep "next"

# Try binding to all interfaces
npm run dev -- -H 0.0.0.0

# Check server logs for errors
npm run dev 2>&1 | tee server.log
```

### Issue: Server appears to "timeout" in terminal

**This is normal behavior!** The development server runs continuously. The "timeout" you see is just the terminal tool giving up waiting for the command to complete.

**What's happening:**
- Server IS running successfully
- Terminal shows "Command timed out" but server continues
- You can access http://localhost:3000 normally

## Server Management Commands

### Start the server
```bash
npm run dev                    # Standard start
./start-dev.sh                 # With automatic cleanup
node run-dev.js               # With health monitoring
```

### Stop the server
```bash
# Press Ctrl+C in the terminal running the server

# Or find and kill the process
lsof -ti :3000 | xargs kill -9
```

### Check server status
```bash
# Check if anything is listening on port 3000
lsof -i :3000

# Test if server is responding
curl http://localhost:3000

# Check Node.js processes
ps aux | grep node
```

## Environment Variables

Make sure `.env.local` exists with:
```env
NEXT_PUBLIC_API_URL=https://podinsight-api.vercel.app
BASIC_AUTH_PASSWORD=your-password-here
```

## Performance Tips

1. **First startup may be slower** - Next.js compiles on first run
2. **Hot reload is automatic** - Changes to code will auto-refresh
3. **Clear cache if needed**: `rm -rf .next`

## Troubleshooting Checklist

If the server won't start:

1. ✓ Check port 3000 is free: `lsof -i :3000`
2. ✓ Verify dependencies installed: `npm install`
3. ✓ Check Node version: `node --version` (should be 18+)
4. ✓ Clear Next.js cache: `rm -rf .next`
5. ✓ Check for syntax errors: `npm run build`
6. ✓ Verify environment variables: `cat .env.local`

## Advanced Debugging

### Enable verbose logging
```bash
DEBUG=* npm run dev
```

### Check for memory issues
```bash
# Increase Node memory limit
NODE_OPTIONS="--max-old-space-size=4096" npm run dev
```

### Network debugging
```bash
# Check all network interfaces
netstat -an | grep LISTEN | grep 3000

# Try different port
PORT=3001 npm run dev
```

## Important Notes

1. **The server runs indefinitely** - This is normal, not an error
2. **"Timeout" messages are expected** - The server is still running
3. **Always check http://localhost:3000** before assuming failure
4. **Use `./start-dev.sh` for most reliable startup**

## Support

If issues persist after trying these solutions:
- Check the GitHub issues: https://github.com/anthropics/claude-code/issues
- Review Next.js docs: https://nextjs.org/docs
- Check error.tsx exists in app/ directory (required by Next.js)

---

Last updated: June 16, 2025