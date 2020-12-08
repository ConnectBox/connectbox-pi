# Makefile to build the given image
.DEFAULT_GOAL := build

DBFLAVORS=mysql postgres

build:
	for DBFLAVOR in $(DBFLAVORS); \
	do \
		packer build -var-file=./vars/centos8.vars.json -var="docker_image_dbflavor=$$DBFLAVOR" moodle-ami.json ; \
		packer build -var-file=./vars/ubuntu1804.vars.json -var="docker_image_dbflavor=$$DBFLAVOR"  moodle-ami.json ; \
		packer build -var-file=./vars/debian10.vars.json -var="docker_image_dbflavor=$$DBFLAVOR"  moodle-ami.json ; \
	done

push:
	for IMAGE in `docker image ls calllearning/*-moodle-ansible --format "{{.Repository}}"`; \
	do \
		docker push $$IMAGE; \
	done
