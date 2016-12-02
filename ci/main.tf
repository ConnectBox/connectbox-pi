# To add:
# - travis-ci keypair?
# - network interface on client-facing-network for server
# - second instance for testing
# - network interface for testing machine
# - see whether I must specific AZ, and whether it can be externalised
# - DHCP options on client-facing VPC so as not to provide addresses?

# add ingress ping to default SG?

# To not add:
# - any ELB stuff

provider "aws" {
	region = "us-east-1"
}

# Shared by all travis-ci jobs
resource "aws_vpc" "default" {
	cidr_block = "10.0.0.0/16"
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
	cidr_block = "10.0.1.0/24"
	availability_zone = "us-east-1b"
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
	vpc_id			= "${aws_vpc.default.id}"

	# SSH access from anywhere
	ingress {
		from_port	 = 0
		to_port		 = 22
		protocol		= "tcp"
		cidr_blocks = ["0.0.0.0/0"]
	}

	# HTTP access from anywhere
	ingress {
		from_port	 = 0
		to_port		 = 80
		protocol		= "tcp"
		cidr_blocks = ["0.0.0.0/0"]
	}

	# outbound internet access
	egress {
		from_port	 = 0
		to_port		 = 0
		protocol		= "-1"
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
	cidr_block = "10.0.2.0/24"
	availability_zone = "us-east-1b"
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
	private_ips = ["10.0.2.5"]
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
	ami = "ami-9d6c128a"
	instance_type = "t2.nano"
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

output "biblebox-server-public-ip" {
	value = "${aws_instance.biblebox-server.public_ip}"
}

