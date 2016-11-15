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
vagrant up;

cat /home/travis/build/edwinsteele/biblebox-pi/ci/.vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory

ansible-playbook -vvvv -i .vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory ../ansible/site.yml

