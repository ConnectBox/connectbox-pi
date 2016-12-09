#!/bin/sh

# Run ansible lint over non-third party modules
#
# Assumes it will be run from the root directory of the checkout i.e.
#  the same directory as .travis.yml

ansible-lint \
	-x ANSIBLE0004,ANSIBLE0010,ANSIBLE0012 \
	--exclude=ansible/roles/mikegleasonjr.firewall \
	--exclude=ansible/roles/geerlingguy.nginx \
	ansible/site.yml
