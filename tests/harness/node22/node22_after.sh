pm2 kill >/dev/null 2>&1; systemctl reset-failed pm2-root; systemctl start pm2-root; sleep 8
echo "pm2-root: $(systemctl is-active pm2-root)"; pm2 ls | grep index | cut -c1-120
ps -o pid,rss,args -C node | cut -c1-110
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
node /tmp/getall.js 2>/dev/null | grep ' = ' > /tmp/get22b.txt
diff /tmp/get16.txt /tmp/get22b.txt && echo "get.* (24) identical to Node 16 run"
for u in /admin/api/ismoodle /admin/api/keepalive /chat /admin/api/apssid; do echo "$u $(curl -s -m 10 -o /dev/null -w '%{http_code}' http://127.0.0.1:5002$u)"; done
echo "via nginx: $(curl -s -m 10 -o /dev/null -w '%{http_code}' http://127.0.0.1/admin/api/ismoodle)"
pm2 logs index --nostream --lines 15 2>/dev/null | tail -12 | cut -c1-150
rm -f /tmp/getall.js
