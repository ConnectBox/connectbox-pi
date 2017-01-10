#!/bin/sh

# This is only run for NON pull requests i.e. merges and comments per suggestion at:
# https://docs.travis-ci.com/user/pull-requests#Pull-Requests-and-Security-Restrictions

# Makes no assumptions about working directory on entry, or the working
#  directory left for subsequent scripts

# Terraform output variables that define endpoints we'll sshe to
PROVISIONED_TARGET_IP_VARIABLES="connectbox-server-public-ip";

# Servers should take 3 minutes max to become accessible over ssh, and as
#  we wait for 1 second between attempts, this is our max attempt count
#MAX_SSH_CONNECT_ATTEMPTS=180;
MAX_SSH_CONNECT_ATTEMPTS=10;

setup_and_verify_infra( ) {
  # Expects arg of PROVISIONED_TARGET_IP_VARIABLES
  # Make sure we don't have an inventory file, as we're going to append to it
  #  as we run this function.
  rm -f inventory;
  terraform apply;

  for target_host_var in $1; do
    conn_attempt_count=0;
    target_host=$(terraform output $target_host_var);

    # Wait for ssh to become available on the target host
    echo -n "Waiting for ssh to become available on $target_host "
    while ! (ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no -i $PEM_OUT admin@$target_host true 2> /dev/null); do
      if [ $conn_attempt_count -gt $MAX_SSH_CONNECT_ATTEMPTS ]; then
	# Something has gone wrong. Bail (don't even attempt to connect to
	#  any other hosts provisioned in the same terraform apply).
	echo "Unable to connect in $conn_attempt_count attempts.";
	exit 1;
      fi
      echo -n ".";
      conn_attempt_count=$(( $conn_attempt_count + 1 ));
      sleep 1;
    done
    echo "OK";
    echo "Adding $target_host to inventory";
    echo "$target_host ansible_ssh_user=admin ansible_ssh_private_key_file=$PEM_OUT" > inventory;
  done

  echo "Inventory follows:";
  cat inventory;
  exit 0;
}

# Extract Encrypted ssh key
cd $TRAVIS_BUILD_DIR;
PEM_OUT=$TRAVIS_BUILD_DIR/ci/travis-ci-connectbox.pem;
touch $PEM_OUT;
chmod 600 $PEM_OUT;
openssl aes-256-cbc -K $encrypted_22a22c63eb0e_key -iv $encrypted_22a22c63eb0e_iv -in ci/travis-ci-connectbox.pem.enc -d >> $PEM_OUT;

# Run CI build on AWS. This uses protected variables
cd $TRAVIS_BUILD_DIR/ci;

setup_and_verify_infra $PROVISIONED_TARGET_IP_VARIABLES;
if [ $? -ne 0 ]; then
  # Try again.
  echo "Tearing down freshly provisioned infrastructure and trying again.";
  terraform destroy --force;
  setup_and_verify_infra $PROVISIONED_TARGET_IP_VARIABLES;
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
  ansible-playbook -i inventory ../ansible/site.yml;

  # Perform a re-run of the playbooks, to see whether they run cleanly and
  #  without marking any task as changed
  ansible-playbook -i inventory ../ansible/site.yml;
else
  # Do essential steps of a deployment to keep things fast
  ansible-playbook -i inventory --skip-tags=full-build-only ../ansible/site.yml;
fi


# Tell the test running host how to find the connectbox by name
# Use tee rather than trying to redirect using sudo
printf "\n%s connectbox.local" ${target_host} | sudo tee -a /etc/hosts > /dev/null
# Run web/selenium tests
TEST_IP=$target_host python -m unittest discover ../tests
