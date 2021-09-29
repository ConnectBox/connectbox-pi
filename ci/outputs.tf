output "connectbox-stretch-server-public-ip" {
	value = "${aws_instance.connectbox-stretch-server.public_ip}"
}
