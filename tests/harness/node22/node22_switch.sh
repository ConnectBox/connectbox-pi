set -e
V=v22.23.4; N=node-$V-linux-armv7l; B=/root/backup-fix60
mkdir -p $B
echo "== backup"
cp -a /root/.pm2/dump.pm2 $B/ 2>/dev/null || true
cp -a /etc/systemd/system/pm2-root.service $B/
cp -a /etc/apt/sources.list.d/nodesource.list $B/
ls -ld /var/www/enhanced/connectbox-manage/node_modules
tar -czf $B/connectbox-manage-node_modules.tgz -C /var/www/enhanced/connectbox-manage node_modules package-lock.json
echo "== stop pm2"
pm2 kill || true
systemctl stop pm2-root || true
echo "== remove Node 16 (apt) and old global pm2"
apt-get remove -y nodejs >/dev/null
mv /usr/lib/node_modules $B/usr_lib_node_modules 2>/dev/null || true
mv /etc/apt/sources.list.d/nodesource.list $B/nodesource.list.disabled
echo "== install Node $V to /usr/local"
tar -xJf /root/$N.tar.xz -C /usr/local --strip-components=1 --exclude=CHANGELOG.md --exclude=LICENSE --exclude=README.md
hash -r; which node npm; node --version; npm --version
echo "== pm2"
npm install -g pm2 2>&1 | tail -2; which pm2; pm2 --version
echo "== connectbox-manage packages"
cd /var/www/enhanced/connectbox-manage && npm install 2>&1 | tail -4
git -C /var/www/enhanced/connectbox-manage status --short | head
echo "== start"
pm2 start /var/www/enhanced/connectbox-manage/src/index.js >/dev/null
sleep 3; pm2 save >/dev/null; pm2 startup 2>&1 | tail -2
grep ExecStart /etc/systemd/system/pm2-root.service
pm2 ls | grep -E "index"
