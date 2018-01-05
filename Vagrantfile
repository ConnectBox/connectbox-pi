# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|

  # Overridden
  config.vm.box = ""

  config.vm.provider "vmware_fusion" do |vmw|
    vmw.memory = "512"
  end
  config.vm.provider "virtualbox" do |vb|
    vb.memory = "512"
  end

  # Debian Stretch
  config.vm.define "stretch" do |stretch|
    stretch.vm.box = "debian/stretch64"
    stretch.vm.network "private_network", ip: "172.28.128.5"
    stretch.vm.post_up_message = "ConnectBox (Debian Stretch) provisioned in developer mode. IP: 172.28.128.5, hostname: stretch-vagrant.connectbox. You probably want '172.28.128.5 stretch-vagrant.connectbox' in /etc/hosts"

    stretch.vm.provision "ansible" do |ansible|
      ansible.playbook = "ansible/site.yml"
      ansible.host_vars = {
        "stretch" => {
          "connectbox_default_hostname": "stretch-vagrant.connectbox",
          "developer_mode": true,
          "lan_dns_if": "eth1",
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
          "lan_dns_if": "eth1",
        }
      }
      ansible.skip_tags = "full-build-only"
    end
  end
end
