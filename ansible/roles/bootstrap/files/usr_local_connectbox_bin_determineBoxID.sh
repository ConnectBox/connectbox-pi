#!/usr/bin/perl

# If a box doesn't have a statically assigned MAC address, such as NEO, we need to craft a boxid (in MAC format) 
# that can be used for phone home
# Derek Maxson, 20211115

# Get eth0 MAC Address
my $mac = `cat /sys/class/net/eth0/address`;

# Get the second character in the string
my $magicBit = substr($mac,1,1);

# Evaluate if the string is indicating a "locally-administered MAC address"
if ($magicBit eq "2" || $magicBit eq "6" ||  lc($magicBit) eq "a" || lc($magicBit) eq "e") {
	#print "Locally Administered\n";
	# Now craft new MAC from machine-id so that it won't change all the time!
	my $machineId = `cat /etc/machine-id`;
	$mac = "0a" . substr($machineId,0,10);
	$mac = join(':', unpack '(A2)*', $mac);
}

print $mac;