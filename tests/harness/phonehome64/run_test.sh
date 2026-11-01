# Run on the box as root, from /tmp/phonehome64 (www-data cannot read /root): tests the new phonehome.py against mock_cloud.py with a
# temporary copy of brand.j2 (bind-mounted in a private mount namespace).
set -e
cd /tmp/phonehome64
rm -f /tmp/mock_cloud.log
python3 mock_cloud.py & M=$!; sleep 2
python3 - <<'PY'
import json
b = json.load(open('/usr/local/connectbox/brand.j2'))
b['server_url'] = 'http://127.0.0.1:8099'; b['server_sitename'] = 'TestSite'
b['server_authorization'] = ''   # let phonehome make one, as on a new box
json.dump(b, open('/tmp/phonehome64/brand_test.j2', 'w'), indent=4)
PY
chmod 666 brand_test.j2
# test copy without the final "do openwellrefresh" (starts lazyLoader downloads)
grep -v 'connectboxmanage do openwellrefresh' new_phonehome.py > phonehome_test.py
chmod 755 phonehome_test.py
unshare -m sh -c 'mount --bind /tmp/phonehome64/brand_test.j2 /usr/local/connectbox/brand.j2 && runuser -u www-data -- /usr/bin/python /tmp/phonehome64/phonehome_test.py' > out.txt 2>&1 || echo "phonehome exit code $?"
kill $M
echo "== phonehome output"; grep -v "^{" out.txt | cut -c1-160
echo "== requests the fake cloud server got"; python3 -c "
import json
for l in open('/tmp/mock_cloud.log'):
    r=json.loads(l); print(r['method'], r['path'], '| auth:', r['auth'], '| body:', r['body'][:200])"
echo "== saved authorization in the test brand: $(python3 -c "import json;print(json.load(open('/tmp/phonehome64/brand_test.j2'))['server_authorization'])")"
echo "== real brand.j2 untouched: server_url=$(python3 -c "import json;b=json.load(open('/usr/local/connectbox/brand.j2'));print(repr(b['server_url']), 'auth len', len(b['server_authorization']))")"
