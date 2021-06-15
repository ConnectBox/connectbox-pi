#!/bin/sh

# This is only run for NON pull requests i.e. merges and comments per suggestion at:
# https://docs.travis-ci.com/user/pull-requests#Pull-Requests-and-Security-Restrictions

# Makes no assumptions about working directory on entry, or the working
#  directory left for subsequent scripts

# Servers should take 3 minutes max to become accessible over ssh, and as
#  we wait for 1 second between attempts, this is our max attempt count
MAX_SSH_CONNECT_ATTEMPTS=180;

setup_and_verify_infra( ) {
  terraform apply;

  for target_host in $(grep -v "^#" ci-inventory | cut -d" " -f1); do
    conn_attempt_count=0;
    # Wait for ssh to become available on the target host
    echo -n "Waiting for ssh to become available on $target_host "
    # The ssh config specifies which user to use and the key
    while ! (ssh -F ci-ssh-config -o ConnectTimeout=2 -o StrictHostKeyChecking=no $target_host true 2> /dev/null); do
      if [ $conn_attempt_count -ge $MAX_SSH_CONNECT_ATTEMPTS ]; then
	# Something has gone wrong. Bail (don't even attempt to connect to
	#  any other hosts provisioned in the same terraform apply).
	echo " unable to connect to $target_host in $conn_attempt_count attempts.";
	return 1;
      fi
      echo -n ".";
      conn_attempt_count=$(( $conn_attempt_count + 1 ));
      sleep 1;
    done
    echo "OK";
  done
  return 0;
}

# Extract Encrypted ssh key
cd $TRAVIS_BUILD_DIR;
PEM_OUT=$TRAVIS_BUILD_DIR/ci/travis-ci-waypoint.pem;
touch $PEM_OUT;
chmod 600 $PEM_OUT;

openssl aes-256-cbc -K $encrypted_6b05639713bb_key -iv $encrypted_6b05639713bb_iv -in ci/travis-ci-waypoint.pem.enc -d >> $PEM_OUT;

# Run CI build on AWS. This uses protected variables
cd $TRAVIS_BUILD_DIR/ci;

setup_and_verify_infra
if [ $? -ne 0 ]; then
  # Try again.
  echo "Tearing down freshly provisioned infrastructure and trying again.";
  terraform destroy --force;
  setup_and_verify_infra
  if [ $? -ne 0 ]; then
    # Something is seriously wrong, and we should bail
    echo "Unable to connect to AWS infrastructure after two attempts. Tearing down freshly provisioned infrastructure and bailing."
    terraform destroy --force;
    exit 1;
  fi
fi

# For builds not triggered by a pull request $TRAVIS_BRANCH is the name
#  of the branch currently being built
if [ "$TRAVIS_BRANCH" = "master" ]; then
  # Do a full deploy and redeploy
  # Now do our initial provisioning run
  # Bomb if ansible bombs
  ansible-playbook -i ci-inventory ../ansible/site.yml || exit 1;
  # Perform a re-run of the playbooks, to see whether they run cleanly and
  #  without marking any task as changed
  ansible-playbook -i ci-inventory -e shutdown_in_image_preparation=False -e do_image_preparation=True ../ansible/site.yml || exit 1;
else
  # Do essential steps of a deployment to keep things fast
  ansible-playbook -i ci-inventory -e shutdown_in_image_preparation=False -e do_image_preparation=True --skip-tags=full-build-only ../ansible/site.yml || exit 1;
fi

# Run web/selenium tests for each host
for target_host in $(grep -v "^#" ci-inventory | cut -d" " -f1); do
  # Break the build if any test fails
  echo "Running tests on $target_host";
  TEST_IP=$(dig +short $target_host) python -m unittest discover ../tests || exit 1;
done
