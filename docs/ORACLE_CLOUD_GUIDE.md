# Oracle Cloud Always Free Guide

## Status on this machine

- **No OCI config / API keys / SSH host found**
- Cloud deployment files are ready
- **Not deployed live** until you create a VM and run the scripts

## What you must do manually (OCI console)

1. Create / sign in to Oracle Cloud (Always Free).
2. Complete any account / payment verification Oracle requires (free tier).
3. Create a **VM.Standard.A1.Flex** (Ampere ARM64) Ubuntu 22.04/24.04 image.
4. Shape suggestion: 2 OCPU, 12 GB RAM, ~50 GB boot volume.
5. Networking: public subnet, assign public IP.
6. Security list / NSG ingress:
   - TCP **22** (your IP only)
   - TCP **80**
   - TCP **443**
7. Download the SSH private key Oracle gives you (keep it private).

## After the VM exists — give the agent (or run yourself)

You need to provide (do not invent):

- Public IP
- SSH user (usually `ubuntu`)
- Path to SSH private key
- Optional domain name

Then on the server:

```bash
# Install Docker (Ubuntu)
sudo apt-get update
sudo apt-get install -y ca-certificates curl
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
# log out/in

# Copy project (from your PC)
# scp -i KEY -r D:\CyberSecurity_FYP ubuntu@IP:~/SENTINEL_X
# Or git clone your private repo

cd ~/SENTINEL_X
cp .env.cloud.example .env.cloud
nano .env.cloud   # set secrets + FRONTEND_ORIGIN=http://YOUR_IP

chmod +x deploy-cloud.sh update-cloud.sh status-cloud.sh backup-cloud.sh restore-cloud.sh
./deploy-cloud.sh
```

## ARM64 images

On Windows with buildx (already available):

```powershell
cd D:\CyberSecurity_FYP
.\scripts\build_multiarch.ps1
# With a registry:
.\scripts\build_multiarch.ps1 -Registry ghcr.io/YOU -Push
```

On the Ampere VM, native `docker compose ... --build` also works (linux/arm64).

## HTTPS (optional)

1. Point a domain A record to the public IP.
2. Use Certbot (host or container) to fill `certbot_certs` volume.
3. Uncomment the TLS server block in `docker/nginx/nginx.prod.conf`.
4. Set `FRONTEND_ORIGIN=https://your.domain`.

## Do not expose

- PostgreSQL
- Redis (not used)
- Docker socket
- SSH to the world
- Kali / lab / Zeek management
