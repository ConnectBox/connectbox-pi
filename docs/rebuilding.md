# Rebuilding Packages & Creating the ConnectBox repository

Due to architectural requirements of some models of the Raspberry Pi, it is necessary to ocassionally rebuild some of the packages used by the ConnectBox (see [Raspberry_Pi_issues](https://wiki.debian.org/RaspberryPi#Raspberry_Pi_issues) for details) and host them in our own repository.

Complete documentation on how to build a package for Debian can be found at their [BuildingTutorial](https://wiki.debian.org/BuildingTutorial), so the steps will only be summarized here.

## Install the toolchain

The easiest way to build compatible packages is directly on the Raspberry Pi 3 (The alternative is going through the effort of setting up a cross compiler toolchain on faster hardware).

    sudo apt-get install build-essential fakeroot devscripts

## Set up a source repository

The robust Debian ecosystem allows us to reproducibly rebuild almost any package without significant effort. One aspect of this is that every major package repository has a cooresponding source repository. For these instructions, add the jessie-backports source repo to apt:

    echo 'deb-src http://ftp.debian.org/debian jessie-backports main contrib' > /etc/apt/sources.list.d/jessie-backports-src.list

## Rebuild the package

Make a directory to work in (the name is not important)

    mkdir debian
    cd debian

Get the source code from the src repo

    apt-get apt-get source libssl-dev

Get the build dependecies (Note: you may run into dependency hell here, since often the reason for rebuilding a package is to get a newer version... which itself requires new libraries... the only way out is to follow the depedencies down, building them too)

    sudo apt-get build-dep libssl-dev

Rebuild the package

    cd openssl-1.0.2k
    debuild -b -uc -us

If all goes well the system will chug for a while and you will have several freshly built packages in your work directory (Somewhat counterituitively, they land outside the directory you ran the debuild command in).

## Make your own repository

There are several tools that will process your packages a create a repository from them - for this example we install and use reprepro:

    apt-get install reprepro

Make a directory for the repository (the name doesn't affect the software, but it should be something that makes sense e.g. "repo"):

    mkdir repo
    cd repo

You'll need to set up a basic configuration for reprepro:

    mkdir conf

Then, in the file `conf/distributions`, place the following:

    Codename: jessie-backports
    Components: main
    Architectures: armhf
    SignWith: 92F3A749

Also place `ask-passphrase` in the file `conf/options` (otherwise reprepro will fail without obvious explanation when it can't sign the repo)

And finally, add your custom packages to the repo:

    reprepro -b . includedeb jessie-backports ../debian/*.deb
    
If everything went well, you should have a custom 'jessie-backports' repo ready to go with your own packages from openssl-1.0.2k

