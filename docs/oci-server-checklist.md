# OCI Always Free — exact manual checklist

Stop here until you finish Oracle account / VM provisioning. Nothing below invents IPs or keys.

## A. Account (manual)

1. Sign up / sign in at https://cloud.oracle.com  
2. Complete any free-tier verification Oracle shows (payment method may be required for Always Free; no paid upgrade needed)  
3. Choose a home region that still has Ampere A1 capacity  

## B. Compute shape (manual)

| Setting | Value |
|---------|--------|
| Image | Ubuntu 22.04 or 24.04 **aarch64** |
| Shape | VM.Standard.A1.Flex (Ampere) |
| OCPU | 2 (or 1 if capacity limited) |
| Memory | up to 12 GB |
| Boot volume | ~50 GB |
| Public IP | Yes |
| VCN | Create new or use default |

## C. Security list / NSG ingress (manual)

| Port | Source | Purpose |
|------|--------|---------|
| 22/tcp | **Your home IP /32 only** | SSH |
| 80/tcp | 0.0.0.0/0 | HTTP / ACME |
| 443/tcp | 0.0.0.0/0 | HTTPS (after certs) |

Do **not** open 5432, 6379, 2375, or lab ports.

## D. What to send the agent (or run yourself)

After the VM exists, provide:

1. Public IP address  
2. SSH username (usually `ubuntu`)  
3. Path to your private SSH key file  
4. Optional domain name  

Then deployment can continue with `deploy-cloud.sh`.

## E. Server install (on the VM)

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
# re-login
cd ~/SENTINEL_X   # after scp/git
cp .env.cloud.example .env.cloud
nano .env.cloud    # secrets + FRONTEND_ORIGIN=http://YOUR_IP
chmod +x deploy-cloud.sh update-cloud.sh status-cloud.sh backup-cloud.sh restore-cloud.sh
./deploy-cloud.sh
```

ARM64 images: build **on the Ampere VM** (recommended). Windows QEMU cross-build of the ML stack is too slow.
