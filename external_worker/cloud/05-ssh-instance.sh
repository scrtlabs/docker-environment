RESOURCE_GROUP_NAME=enigma-external-worker
VM_NAME=enigma-external-worker
VM_PUBLIC_IP=$(az vm show -d -g $RESOURCE_GROUP_NAME -n $VM_NAME  --query publicIps -o json | tr -d '"')

ssh -i enigma.key enigma@$VM_PUBLIC_IP