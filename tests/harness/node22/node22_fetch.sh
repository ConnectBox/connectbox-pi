set -e
V=v22.23.4; N=node-$V-linux-armv7l
cd /root
curl -s -m 60 -O https://nodejs.org/dist/$V/SHASUMS256.txt
curl -s -m 300 -O https://nodejs.org/dist/$V/$N.tar.xz
grep " $N.tar.xz\$" SHASUMS256.txt | sha256sum -c -
mkdir -p /opt && tar -xJf $N.tar.xz -C /opt
/opt/$N/bin/node --version
/opt/$N/bin/node -p "process.versions.openssl + ' ' + process.arch"
echo native modules:; find /var/www/enhanced/connectbox-manage/node_modules -name '*.node' | head
echo other node users:; grep -rlI --exclude-dir=node_modules -e '^#!.*node' /usr/local/connectbox /usr/local/bin 2>/dev/null | head
ls /etc/systemd/system | grep -i pm2; grep -E "ExecStart|Environment=PATH" /etc/systemd/system/pm2-root.service
