#!/bin/sh

# The inventory file is used by lots of people, and when populated, contains
#  info that is only relevant to a specific person. We make sure that it only
#  contains comments/template for others to follow, but no actual entries.
#
# Assumes it will be run in the root of the checkout i.e. at the same level
#  as .travis.yml

echo "Confirming inventory file only contains comments."
count=$(grep -c -v "^#" ansible/inventory);
if [ $count -gt 0 ]; then
    echo "FAIL: Inventory file contains ${count} non-comment lines";
    exit 1;
else
    echo "PASS: Inventory only contains comment lines";
    exit 0;
fi
