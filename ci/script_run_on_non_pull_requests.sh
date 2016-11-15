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

ls -l ci;
md5sum ci/*.pem;
cat /home/travis/build/edwinsteele/biblebox-pi/ci/.vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory
echo "AWS_ACCESS_KEY_ID"
echo $AWS_ACCESS_KEY_ID | md5sum
echo "AWS_SECRET_ACCESS_KEY"
echo $AWS_SECRET_ACCESS_KEY | md5sum

# Run CI build on AWS. This uses protected variables
cd $TRAVIS_BUILD_DIR/ci;
vagrant up;

find $TRAVIS_BUILD_DIR/ci/.vagrant

ansible-playbook -vvvv -i .vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory ../ansible/site.yml

