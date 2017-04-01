# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.box = "debian/jessie64"
  config.vm.network "private_network", ip: "172.28.128.3"
  config.vm.define "connectbox"
  config.vm.post_up_message = "ConnectBox provisioned in developer mode. IP: 172.28.128.3, hostname: connectbox.debian-vagrant. You probably want '172.28.128.3 connectbox.debian-vagrant' in /etc/hosts"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "1024"
  end

  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "ansible/site.yml"
    ansible.extra_vars = {
      developer_mode: true,
      connectbox_default_hostname: "connectbox.debian-vagrant"
    }
    ansible.skip_tags = "full-build-only"
  end
end
