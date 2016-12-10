variable "region" { default = "us-east-1" }

# Seemingly required so subnets are not necessarily created in the same AZ as
#  the network interfaces
variable "preferred_az" {
	default = {
		"us-east-1" = "us-east-1b"
		"ap-southeast-1" = "ap-southeast-1a"
	}
}

variable "instance_type" { default = "t2.nano" } 

# Debian Jessie AMIs by region1
variable "amis" {
	default = {
		"us-east-1" = "ami-9d6c128a"
		"ap-southeast-1" = "ami-0e6dce6d"
	}
}

variable "default_vpc_cidr" { default = "10.0.0.0/16" }
variable "default_subnet_cidr" { default = "10.0.1.0/24" }
variable "client_facing_subnet_cidr" { default = "10.0.2.0/24" }

variable "server_client_facing_ip" { default = "10.0.2.5" }
