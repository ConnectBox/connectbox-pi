output "waypoint-stretch-server-public-ip" {
	value = "${aws_instance.waypoint-stretch-server.public_ip}"
}
