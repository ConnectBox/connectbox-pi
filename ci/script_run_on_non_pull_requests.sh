#!/bin/sh

# This is only run for NON pull requests i.e. merges and comments per suggestion at:
# https://docs.travis-ci.com/user/pull-requests#Pull-Requests-and-Security-Restrictions

# Makes no assumptions about working directory on entry, or the working
#  directory left for subsequent scripts

# Extract Encrypted ssh key
cd $TRAVIS_BUILD_DIR;
PEM_OUT=$TRAVIS_BUILD_DIR/ci/travis-ci-biblebox.pem;
touch $PEM_OUT;
chmod 600 $PEM_OUT;
openssl aes-256-cbc -K $encrypted_22a22c63eb0e_key -iv $encrypted_22a22c63eb0e_iv -in ci/travis-ci-biblebox.pem.enc -d >> $PEM_OUT;

# Run CI build on AWS. This uses protected variables
cd $TRAVIS_BUILD_DIR/ci;

date
terraform apply;
date

ping -c 5 dynamodb.us-east-1.amazonaws.com
ping -c 5 dynamodb.us-west-1.amazonaws.com
ping -c 5 dynamodb.us-west-2.amazonaws.com
ping -c 5 dynamodb.eu-west-1.amazonaws.com
ping -c 5 dynamodb.eu-central-1.amazonaws.com
ping -c 5 dynamodb.ap-south-1.amazonaws.com
ping -c 5 dynamodb.ap-northeast-2.amazonaws.com
ping -c 5 dynamodb.ap-southeast-1.amazonaws.com
ping -c 5 dynamodb.ap-southeast-2.amazonaws.com
ping -c 5 dynamodb.ap-northeast-1.amazonaws.com
ping -c 5 dynamodb.sa-east-1.amazonaws.com
ping -c 5 dynamodb.cn-north-1.amazonaws.com.cn

target_host=$(terraform output biblebox-server-public-ip);

# Create an inventory file suitable for ansible
echo "${target_host} ansible_ssh_user=admin ansible_ssh_private_key_file=$PEM_OUT" > inventory;
cat inventory;

# Wait for ssh to become available
while ! (ssh -o ConnectTimeout=2 -i ${PEM_OUT} admin@${target_host} /usr/bin/true 2> /dev/null); do
  echo -n ".";
done
echo "OK";

# Now do our initial provisioning run
date
ansible-playbook -i inventory ../ansible/site.yml;
date

# Perform a re-run of the playbooks, to see whether they run cleanly and
#  without marking any task as changed
date
ansible-playbook -i inventory ../ansible/site.yml;
date

# Tell the test running host how to find the biblebox by name
echo "\n${target_host} biblebox.local" | sudo tee -a /etc/hosts > /dev/null
# Run web/selenium tests
date
TEST_IP=$target_host python -m unittest discover ../tests
date
