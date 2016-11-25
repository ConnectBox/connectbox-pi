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
vagrant up --no-provision;

# We need to assemble an inventory file ourselves. If we use the one that
#  vagrant automatically creates, it has the hostname as "default" which
#  confuses the ansible synchronize task. The synchronize task has some
#  logic that determines whether the rsync arguments involve a remote host
#  and because "default" doesn't match the machine name, it thinks that
#  the remote endpoint requires an ssh connection, and because keys aren't
#  accessible, the connection fails.
# So we assemble an inventory file ourselves.
target_host=$(vagrant ssh-config | awk '$1 ~ /HostName/ { print $2; }')
ssh_user=$(vagrant ssh-config | awk '$1 ~ /User/ { print $2; }')
echo "$target_host ansible_ssh_user=$ssh_user ansible_ssh_private_key_file=$PEM_OUT" > $INVENTORY_FILE;

# Now do our initial provisioning run
vagrant provision

# Perform a re-run of the playbooks, to see whether they run cleanly and
#  without marking any task as changed
vagrant provision
