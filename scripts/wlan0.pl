#!/usr/bin/perl

# This program does steps necessary to unblock (rfkill) and init the wlan0 for client Wi-Fi on RPi

my $rfkill = `sudo rfkill list 0 |grep 'Soft blocked: yes'`;

print "rfkill says: $rfkill\n";

if ($rfkill =~ /yes/) {
	print "Unkilling the rfkill for wlan0\n";
	system ("rfkill unblock 0");
	system ("/usr/local/connectbox/bin/wlan0.pl &");
}
else {
	system ("ifdown wlan0");
	system ("ifup wlan0");
}
