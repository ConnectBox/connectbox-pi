output "connectbox-debian-server-public-ip" {
	value = "${aws_instance.connectbox-debian-server.public_ip}"
}
