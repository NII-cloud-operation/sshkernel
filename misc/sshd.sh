#!/bin/bash -xe

#
# Launch sshd at admin@localhost:2222
#

docker kill sshd || true
docker rm sshd || true
ssh-keygen -R [localhost]:2222

docker run \
  -d \
  -p 2222:22 \
  --name sshd \
  -e SSH_USERS=admin:1000:1000 \
  -v $PWD/id_rsa.pub:/etc/authorized_keys/admin \
  -v $PWD/id_rsa.pub:/root/.ssh/authorized_keys \
  docker.io/panubo/sshd

echo done
