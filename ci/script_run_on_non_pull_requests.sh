#!/bin/sh

# This is only run for NON pull requests i.e. merges and comments per suggestion at:
# https://docs.travis-ci.com/user/pull-requests#Pull-Requests-and-Security-Restrictions

# Makes no assumptions about working directory on entry, or the working
#  directory left for subsequent scripts

# Extract Encrypted ssh key
pushd $TRAVIS_BUILD_DIR;
openssl aes-256-cbc -K $encrypted_22a22c63eb0e_key -iv $encrypted_22a22c63eb0e_iv -in ci/travis-ci-biblebox.pem.enc -out ci/travis-ci-biblebox.pem -d;
popd;

# Run CI build on AWS. This uses protected variables
pushd $TRAVIS_BUILD_DIR/ci;
vagrant up --no-provision;
popd;


