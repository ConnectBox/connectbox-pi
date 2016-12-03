# To add:
# - travis-ci keypair?
# - network interface on client-facing-network for server
# - second instance for testing
# - network interface for testing machine
# - see whether I must specific AZ, and whether it can be externalised
# - DHCP options on client-facing VPC so as not to provide addresses?

provider "aws" {
	region = "${var.region}"
}

# Shared by all travis-ci jobs
resource "aws_vpc" "default" {
	cidr_block = "${var.default_vpc_cidr}"
	tags {
		Name = "default-travis-ci-vpc"
		project = "biblebox"
		lifecycle = "ci"
		creator = "terraform"
	}
}

# Access for the default VPC
resource "aws_internet_gateway" "default" {
	vpc_id = "${aws_vpc.default.id}"
	tags {
		Name = "default-travis-ci-vpc-internet-gateway"
		project = "biblebox"
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
		project = "biblebox"
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
		project = "biblebox"
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
		project = "biblebox"
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
		instance = "${aws_instance.biblebox-server.id}"
		device_index = 1
	}
	tags {
		Name = "client-facing interface for biblebox server"
		project = "biblebox"
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
#		instance = "${aws_instance.biblebox-server.id}"
#		device_index = 1
#	}
#	tags {
#		Name = "default interface for biblebox server"
#		project = "biblebox"
#		lifecycle = "ci"
#		creator = "terraform"
#	}
#}

resource "aws_instance" "biblebox-server" {
	ami = "${lookup(var.amis, var.region)}"
	instance_type = "${var.instance_type}"
	key_name = "travis-ci-biblebox"
	subnet_id = "${aws_subnet.default.id}"
	security_groups = ["${aws_security_group.default.id}"]
	tags {
		Name = "biblebox-server"
		project = "biblebox"
		lifecycle = "ci"
		creator = "terraform"
	}
}
