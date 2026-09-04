#!/usr/bin/env bash
# Create a personal-Azure Linux VM and run Optival + Ollama via Docker Compose.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RG="${AZURE_RG:-optival-rg}"
VM_NAME="${AZURE_VM_NAME:-optival-vm}"
ADMIN_USER="${AZURE_ADMIN_USER:-azureuser}"
MODEL="${DEFAULT_MODEL:-}"

# Free-trial SKUs are often capacity-blocked in eastus. Try several cheap sizes/regions.
# B2s = 4 GB RAM → small model. D2s_v3 / B2ms = 8 GB → 7b-class model.
FALLBACKS=(
  "westus2|Standard_B2s|llama3.2:3b"
  "westus|Standard_B2s|llama3.2:3b"
  "eastus|Standard_B2s|llama3.2:3b"
  "eastus2|Standard_B2s|llama3.2:3b"
  "centralus|Standard_B2s|llama3.2:3b"
  "westeurope|Standard_B2s|llama3.2:3b"
  "northeurope|Standard_B2s|llama3.2:3b"
  "westus2|Standard_D2s_v3|qwen2.5:7b"
  "eastus|Standard_D2s_v3|qwen2.5:7b"
  "westus|Standard_D2s_v3|qwen2.5:7b"
  "westus2|Standard_B1s|llama3.2:1b"
)

if [[ -n "${AZURE_LOCATION:-}" && -n "${AZURE_VM_SIZE:-}" ]]; then
  FALLBACKS=("${AZURE_LOCATION}|${AZURE_VM_SIZE}|${DEFAULT_MODEL:-llama3.2:3b}")
fi

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI not found. Install: https://learn.microsoft.com/cli/azure/install-azure-cli"
  exit 1
fi

echo "Signing in to Azure (browser will open if needed)..."
az account show >/dev/null 2>&1 || az login

SUB="$(az account show --query id -o tsv)"
SUB_NAME="$(az account show --query name -o tsv)"
echo "Subscription: $SUB_NAME ($SUB)"

LOCATION=""
VM_SIZE=""
CHOSEN_MODEL=""
CREATED=0

for spec in "${FALLBACKS[@]}"; do
  IFS='|' read -r LOCATION VM_SIZE CHOSEN_MODEL <<<"$spec"
  if [[ -n "$MODEL" ]]; then
    CHOSEN_MODEL="$MODEL"
  fi
  echo
  echo "Trying VM $VM_NAME  size=$VM_SIZE  location=$LOCATION  model=$CHOSEN_MODEL"
  if az group show --name "$RG" >/dev/null 2>&1; then
    RG_LOC="$(az group show --name "$RG" --query location -o tsv)"
    echo "  Resource group $RG already exists in $RG_LOC (VM region can differ)."
  else
    az group create --name "$RG" --location "$LOCATION" >/dev/null
  fi
  if az vm create \
    --resource-group "$RG" \
    --name "$VM_NAME" \
    --location "$LOCATION" \
    --image Ubuntu2204 \
    --size "$VM_SIZE" \
    --admin-username "$ADMIN_USER" \
    --generate-ssh-keys \
    --public-ip-sku Standard \
    --storage-sku Standard_LRS \
    --security-type Standard \
    --os-disk-size-gb 64 \
    --output json >/tmp/optival-vm.json 2>/tmp/optival-vm.err; then
    CREATED=1
    break
  fi
  echo "  Not available. Next option..."
  python3 - <<'PY' 2>/dev/null || grep -E "SkuNotAvailable|Quota|Location|Message:|Code:" /tmp/optival-vm.err | head -n 12
import re
text = open("/tmp/optival-vm.err", errors="ignore").read()
msgs = re.findall(r"Message: ([^\n]+)", text)
codes = re.findall(r"Code: (\w+)", text)
if msgs:
    print("  Azure:", msgs[0][:300])
elif codes:
    print("  Azure:", codes[0])
PY
done

if [[ "$CREATED" -ne 1 ]]; then
  echo
  echo "Could not create a VM. Free Trial often has no spare B4ms/B-series in eastus."
  echo "Full error is in /tmp/optival-vm.err"
  exit 1
fi

IP="$(az vm show -d -g "$RG" -n "$VM_NAME" --query publicIps -o tsv)"
echo "VM public IP: $IP  ($VM_SIZE in $LOCATION)"

az vm open-port --resource-group "$RG" --name "$VM_NAME" --port 80 --priority 1001 >/dev/null
az vm open-port --resource-group "$RG" --name "$VM_NAME" --port 8000 --priority 1002 >/dev/null

echo "Installing Docker on the VM..."
az vm run-command invoke \
  --resource-group "$RG" \
  --name "$VM_NAME" \
  --command-id RunShellScript \
  --scripts "
    set -e
    apt-get update
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \$VERSION_CODENAME) stable\" > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    usermod -aG docker ${ADMIN_USER}
  " >/dev/null

echo "Copying project to the VM (excludes .venv / node_modules)..."
ssh -o StrictHostKeyChecking=accept-new "${ADMIN_USER}@${IP}" "mkdir -p ~/optival"
rsync -az --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/dist' \
  --exclude 'api_data' \
  --exclude '__pycache__' \
  "${ROOT}/" "${ADMIN_USER}@${IP}:~/optival/"

echo "Building and starting containers (first model pull can take 10+ minutes)..."
ssh "${ADMIN_USER}@${IP}" "cd ~/optival && DEFAULT_MODEL='${CHOSEN_MODEL}' sudo docker compose up -d --build"

echo
echo "Optival should be reachable at:"
echo "  http://${IP}"
echo "  http://${IP}:8000"
echo
echo "Health check:  curl http://${IP}:8000/api/health"
echo "Stop credit use:  az vm deallocate -g ${RG} -n ${VM_NAME}"
echo "Delete all:       az group delete -n ${RG} --yes --no-wait"
echo
echo "Do not upload real ERAS PDFs to a personal Azure account (FERPA)."
