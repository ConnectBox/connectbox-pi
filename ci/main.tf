# To add:
# - network interface on client-facing-network for server
# - second instance for testing
# - network interface for testing machine
# - see whether I must specific AZ, and whether it can be externalised
# - DHCP options on client-facing VPC so as not to provide addresses?

provider "aws" {
	region = "${var.region}"
}

# Key pairs aren't removed when a terraform destroy is performed, so having
#  this resource definition causes warnings on every terraform apply. This
#  is left here to make it easier to do the first run in a new region, or
#  the first run after a complete cleanup or in a new account.
#
#resource "aws_key_pair" "travis-ci-connectbox" {
#	key_name = "travis-ci-connectbox"
#	public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCqWQb/Iv6kos8F/f9CEiXorP61L+nPemJFI1ML9OsBabN9e5PGII6xStEa6aDUPFqKB1ysMiYEaSn6hH3SzV5GD0/tWkLncHrJKAZ+FuXeOgAINU4TJnnspZhlsVrfEVp2moBQZfGPNpFmRJz4sn5xXHj2sWpozcxdEvC08ipE1yE4Vz10eicY500QUpJlPvHYxMaLeD7Znl68gAtQbuAPtKGvoxzf9fQlAGwBEuWnEs35NSh+WNqYr/yi7jAPiN6JrXK0y1TBhauiYN8HZ0JaeMjGIUY+Wntvm3jaWLOKc1f2ZHrKdaydZ8Jl8wTsq8pZf7BKuWD7rYqiVGdRRqQ1"
#}

# Shared by all travis-ci jobs
resource "aws_vpc" "default" {
	cidr_block = "${var.default_vpc_cidr}"
	tags {
		Name = "default-travis-ci-vpc"
		project = "connectbox"
		lifecycle = "ci"
		creator = "terraform"
	}
}

# Access for the default VPC
resource "aws_internet_gateway" "default" {
	vpc_id = "${aws_vpc.default.id}"
	tags {
		Name = "default-travis-ci-vpc-internet-gateway"
		project = "connectbox"
		lifecycle = "ci"
		creator = "terraform"
	}
}

# A route for the default VPC to its internet gateway
resource "aws_route" "internet_access" {
	route_table_id = "${aws_vpc.default.main_route_table_id}"
	destination_cidr_block = "0.0.0.0/0"
	gateway_id = "${aws_internet_gateway.default.id}"
}

# A subnet in the default VPC for our instances
resource "aws_subnet" "default" {
	vpc_id = "${aws_vpc.default.id}"
	cidr_block = "${var.default_subnet_cidr}"
	availability_zone = "${lookup(var.preferred_az, var.region)}"
	map_public_ip_on_launch = true
	tags {
		Name = "default-travis-ci-vpc-subnet"
		project = "connectbox"
		lifecycle = "ci"
		creator = "terraform"
	}
}

resource "aws_security_group" "default" {
	description = "default security group for travis-ci jobs"
	vpc_id = "${aws_vpc.default.id}"

	# SSH access from anywhere
	ingress {
		from_port = 0
		to_port = 22
		protocol = "tcp"
		cidr_blocks = ["0.0.0.0/0"]
	}

	# HTTP access from anywhere
	ingress {
		from_port = 0
		to_port = 80
		protocol = "tcp"
		cidr_blocks = ["0.0.0.0/0"]
	}

	# ICMP Unreachable
	ingress {
		from_port = 3
		to_port = 0
		protocol = "icmp"
		cidr_blocks = ["0.0.0.0/0"]
	}

	# ICMP Echo Request
	ingress {
		from_port = 8
		to_port = 0
		protocol = "icmp"
		cidr_blocks = ["0.0.0.0/0"]
	}

	# outbound internet access
	egress {
		from_port = 0
		to_port = 0
		protocol = "-1"
		cidr_blocks = ["0.0.0.0/0"]
	}

	tags {
		Name = "travis-ci-default-sg"
		project = "connectbox"
		lifecycle = "ci"
		creator = "terraform"
	}
}


resource "aws_subnet" "client-facing-subnet" {
	vpc_id = "${aws_vpc.default.id}"
	cidr_block = "${var.client_facing_subnet_cidr}"
	availability_zone = "${lookup(var.preferred_az, var.region)}"
	tags {
		Name = "client-facing-subnet"
		project = "connectbox"
		lifecycle = "ci"
		creator = "terraform"
	}
}

resource "aws_network_interface" "client-facing-server" {
	subnet_id = "${aws_subnet.client-facing-subnet.id}"
	# AWS reserves the bottom four addresses in each subnet
	#  so this is the lowest available
	private_ips = ["${var.server_client_facing_ip}"]
	attachment {
		instance = "${aws_instance.connectbox-server.id}"
		device_index = 1
	}
	tags {
		Name = "client-facing interface for connectbox server"
		project = "connectbox"
		lifecycle = "ci"
		creator = "terraform"
	}
}

#resource "aws_network_interface" "default-server" {
#	subnet_id = "${aws_subnet.default.id}"
#	# AWS reserves the bottom four addresses in each subnet
#	#  so this is the lowest available
#	private_ips = ["10.0.1.5"]
#	security_groups = ["${aws_security_group.default.id}"]
#	attachment {
#		instance = "${aws_instance.connectbox-server.id}"
#		device_index = 1
#	}
#	tags {
#		Name = "default interface for connectbox server"
#		project = "connectbox"
#		lifecycle = "ci"
#		creator = "terraform"
#	}
#}

resource "aws_instance" "connectbox-server" {
	ami = "${lookup(var.amis, var.region)}"
	instance_type = "${var.instance_type}"
	key_name = "travis-ci-connectbox"
	subnet_id = "${aws_subnet.default.id}"
	vpc_security_group_ids = ["${aws_security_group.default.id}"]
	tags {
		Name = "connectbox-server"
		project = "connectbox"
		lifecycle = "ci"
		creator = "terraform"
	}
}
