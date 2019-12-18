RESOURCE_GROUP_NAME=enigma-external-worker
VM_NAME=enigma-external-worker
VM_IMAGE=microsoft-aks:aks:aks-ubuntu-1804-201911:2019.11.18
VM_SIZE=Standard_DC2s

az vm create -n $VM_NAME -g $RESOURCE_GROUP_NAME --image $VM_IMAGE   \
    --public-ip-address enigma-external-worker-ip --size $VM_SIZE  \
    --admin-username enigma --ssh-key-value enigma.key.pub --custom-data cloud-init.txt