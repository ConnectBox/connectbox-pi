output "biblebox-server-public-ip" {
	value = "${aws_instance.biblebox-server.public_ip}"
}
