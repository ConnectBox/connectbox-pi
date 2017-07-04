variable "region" { default = "us-west-2" }

# So that dev of CI can happen alongside real CI builds
variable "ci-dns-prefix" { default = "ci" }

# Seemingly required as subnets are not necessarily created in the same AZ as
#  the network interfaces
variable "preferred_az" {
	default = {
		"us-east-1" = "us-east-1b"
		"ap-southeast-2" = "ap-southeast-2a"
		"us-west-2" = "us-west-2a"
	}
}

variable "instance_type" { default = "t2.nano" }

# Debian Jessie AMIs by region
variable "debian_amis" {
	default = {
		"us-east-1" = "ami-b14ba7a7"
		"ap-southeast-2" = "ami-881317eb"
		"us-west-2" = "ami-221ea342"
	}
}

# Ubuntu xenial AMIs by region (hvm:ebs-ssd) (instance store unsupp on nano)
# From: https://cloud-images.ubuntu.com/locator/ec2/
variable "ubuntu_amis" {
	default = {
		"us-east-1" = "ami-d15a75c7"
		"ap-southeast-2" = "ami-e94e5e8a"
		"us-west-2" = "ami-835b4efa"
	}
}

variable "default_vpc_cidr" { default = "10.0.0.0/16" }
variable "default_subnet_cidr" { default = "10.0.1.0/24" }
variable "client_facing_subnet_cidr" { default = "10.0.2.0/24" }

variable "debian_server_client_facing_ip" { default = "10.0.2.5" }
variable "ubuntu_server_client_facing_ip" { default = "10.0.2.6" }
