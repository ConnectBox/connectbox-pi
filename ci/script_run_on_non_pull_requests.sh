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

terraform apply;

# Create an inventory file suitable for ansible
echo "$(terraform output biblebox-server-public-ip) ansible_ssh_user=admin ansible_ssh_private_key_file=$PEM_OUT" > inventory;
cat inventory;

# Now do our initial provisioning run
ansible-playbook -i inventory ../site.yml;

# Perform a re-run of the playbooks, to see whether they run cleanly and
#  without marking any task as changed
ansible-playbook -i inventory ../site.yml;
