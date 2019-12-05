az vm create -n enigma-external-worker -g enigma-external-worker --image UbuntuLTS  \
    --public-ip-address enigma-external-worker-ip --size Standard_DC2s  \
    --admin-username enigma --ssh-key-value enigma.key  # --custom-data cloud-init.txt
