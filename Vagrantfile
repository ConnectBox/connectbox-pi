# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|

  # Overridden
  config.vm.box = ""

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "512"
  end

  # Debian Jessie
  config.vm.define "debian" do |debian|
    debian.vm.box = "debian/jessie64"
    debian.vm.network "private_network", ip: "172.28.128.3"
    debian.vm.post_up_message = "ConnectBox (Debian Jessie) provisioned in developer mode. IP: 172.28.128.3, hostname: debian-vagrant.connectbox. You probably want '172.28.128.3 debian-vagrant.connectbox' in /etc/hosts"

    debian.vm.provision "ansible" do |ansible|
      ansible.playbook = "ansible/site.yml"
      ansible.host_vars = {
	      "debian" => {
          "connectbox_default_hostname": "debian-vagrant.connectbox",
          "developer_mode": true,
	}
      }
      ansible.skip_tags = "full-build-only"
    end
  end

  # Ubuntu Xenial
  config.vm.define "ubuntu" do |ubuntu|
    # Not using ubuntu/xenial64 because of
    #  https://bugs.launchpad.net/cloud-images/+bug/1569237
    ubuntu.vm.box = "bento/ubuntu-16.04"
    ubuntu.vm.network "private_network", ip: "172.28.128.4"
    ubuntu.vm.post_up_message = "ConnectBox (Ubuntu Xenial) provisioned in developer mode. IP: 172.28.128.4, hostname: ubuntu-vagrant.connectbox. You probably want '172.28.128.4 ubuntu-vagrant.connectbox' in /etc/hosts"

    ubuntu.vm.provision "ansible" do |ansible|
      ansible.playbook = "ansible/site.yml"
      ansible.host_vars = {
        "ubuntu" => {
          "connectbox_default_hostname": "ubuntu-vagrant.connectbox",
          "developer_mode": true,
	}
      }
      ansible.skip_tags = "full-build-only"
    end
  end
end
