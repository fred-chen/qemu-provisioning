# qemu-provisioning
Provision a qemu virtual machine cluster from command line.


## Command line

```bash
cluster.py deploy -f template.yaml
```

## Cluster config file format

```yaml
# following cluster definition will create a cluster
# with nodes: node.chenp.net, node1.chenp.net, node2.chenp.net ... node4.chenp.net
# with IP address from 10.1.0.60 ~ 10.1.0.64

clusterName: test_template
domainName: chenp.net
imagePath: https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img
guestOs: Ubuntu
systemDiskSize: 20g
dataDiskSizes:
- 100g
- 90g
- 80g
- 70g
cpu: 2
mem: 4g
mtu: 9000
gateway: 10.1.0.1
nameserver: 10.1.0.1
authorized-keys:
- "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCj9kw9XEd5A7WUi1MvPsN/382evcwtt+2Loos2ztrnXsYewQArW0ePMX6CVT0+RrhqKMhxkwZMRQePqIzZBhzWPiv+PFB7obCyh6RJb7utOv3aF4A646zuG9ch8t69Ik/hsV2B6Qe4PZb4h+eHOMbixT3AR556W1HKSfxDJKJ4bULxEJEkHqnaP8V4P0+cP3qB3NxTNx+o9hjoSTx+YTDjYRY7mVIesnfKnYImsaFapsvOacw1xUv0s25Iy2cQFUI32rt2PTb+ZXFJLynbOVvGvA+ATR3qa99KICx8LT2BzUvYEypfrmw0uuRGwsIk4tvVO7DINoONBSqHGv/QaYX9 fred@mac.chenp.net"
- "ssh-dss AAAAB3NzaC1kc3MAAACBANVJJTojvKCttZaRkoEC7yfG91if4kuoxTf+U5OIHawLO/sdWwsbMNv9HXKPOPJEXSpmkg3RkxEX5DPgDYUGfhbxZ2NqbRGQtvlRKCqXfqCcgN52X+dediYTa0RKZMU6PTVikarOXjm4SCimaXHiB0Yc7BYnssmgTBxWTz6ITCIvAAAAFQCM5lkwlDs8k9izsmCQn1rNHNYk0wAAAIAjuUvWOSiGxX0fVjb/lWipF9AAgv9p/ORwsQnsovJwZtjs9MwcdsAoPhg22YX/2nrU/wL9LubRsU0BnPK8+0ZE3Z45hagJwR9R9I2Ozixbs110z9Hx31ensNSi4oB6YZeTMVaW8DO7bTxNgHUdNjSyOrUAJf5ywBryOsqUzaqfFAAAAIAlGuBcgBoSlgly+PEd6KffHDmwyzDndJHbohvrESqWH+N0yAOHUKNRAGVYW+HwcwP5grDR3RiAhZ85MyT+CETK4JDZB+BBUIKiRK1Vk62c7ZikBRbW8jN8IMczCNV0dgeKEn2H9KkZqEJxvSgcXlsYxakw8KKh++lkndWKfqK3nA== fred@mac.chenp.net"
nodes:
- name: node
  ipAddress: 10.1.0.60/24
- name: node1
  ipAddress: 10.1.0.61/24
- name: node2
  ipAddress: 10.1.0.62/24
- name: node3
  ipAddress: 10.1.0.63/24
- name: node4
  ipAddress: 10.1.0.64/24
```

## Install

```bash
git clone https://github.com/fred-chen/qemu-provisioning.git
cd qemu-provisioning
./init.sh <cloud_image_folder>
```
