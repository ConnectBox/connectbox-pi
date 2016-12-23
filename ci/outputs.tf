output "connectbox-server-public-ip" {
	value = "${aws_instance.connectbox-server.public_ip}"
}
