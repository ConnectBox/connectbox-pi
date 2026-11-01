N=/opt/node-v22.23.4-linux-armv7l/bin/node
cd /var/www/enhanced/connectbox-manage
cat > /tmp/getall.js <<'JS'
const crypto=require('crypto');
const f=require('/var/www/enhanced/connectbox-manage/src/functions.js');
const skip=['syncweblog','clientwifiscan','subscriptions'];
const secret=['appassphrase','clientpassphrase'];
const g=f.get||f;
for (const k of Object.keys(g).sort()) {
  if (typeof g[k]!=='function'||skip.includes(k)) continue;
  let v; try { v=g[k](); } catch(e){ v='THROW '+e.message; }
  let s=JSON.stringify(v);
  if (secret.includes(k)) s='sha256:'+crypto.createHash('sha256').update(String(s)).digest('hex').slice(0,12);
  if (s && s.length>200) s=s.length+' chars sha256:'+crypto.createHash('sha256').update(s).digest('hex').slice(0,12);
  console.log(k+' = '+s);
}
JS
echo "== exports"; node -e "const f=require('./src/functions.js'); console.log(Object.keys(f).join(' '))" 2>/dev/null | tail -1
node /tmp/getall.js 2>/dev/null | grep ' = ' > /tmp/get16.txt
$N /tmp/getall.js 2>/tmp/get22.err | grep ' = ' > /tmp/get22.txt
echo "== get.* lines node16: $(wc -l </tmp/get16.txt) node22: $(wc -l </tmp/get22.txt)"
diff /tmp/get16.txt /tmp/get22.txt && echo "get.* outputs identical"
echo "== node22 stderr (warnings):"; grep -v '^get\.\|^[a-z]*: ' /tmp/get22.err | sort | uniq | head -10
echo "== server under node22 on port 5012"
CHATHOST_PORT=5012 $N src/index.js >/tmp/n22.log 2>&1 &
P=$!; sleep 12
for u in /admin/api/ismoodle /admin/api/keepalive /chat /admin/api/apssid /admin/api/brand/Brand /admin/api/do/reboot; do
 a=$(curl -s -m 10 -o /tmp/a -w '%{http_code}' http://127.0.0.1:5002$u); b=$(curl -s -m 10 -o /tmp/b -w '%{http_code}' http://127.0.0.1:5012$u)
 echo "$u 16:$a 22:$b $(cmp -s /tmp/a /tmp/b && echo same-body || echo DIFF-body)"
done
a=$(curl -s -m 10 -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/json' -d '{}' http://127.0.0.1:5002/admin/api/auth); b=$(curl -s -m 10 -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/json' -d '{}' http://127.0.0.1:5012/admin/api/auth); echo "PUT auth (empty) 16:$a 22:$b"
echo "== node22 server memory (RSS kB): $(ps -o rss= -p $P)"; echo "node16 server RSS kB: $(ps -o rss= -p $(pgrep -f 'connectbox-manage/src/index.js' | grep -v $P | head -1))"
kill $P; sleep 1
echo "== node22 server log:"; grep -v '^CHATHOST' /tmp/n22.log | head -15
rm -f /tmp/getall.js /tmp/a /tmp/b
