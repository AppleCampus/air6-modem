#!/usr/bin/env python3
"""Verify pinned inputs, build, and absence of the private authorization runtime."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
r=Path(__file__).resolve().parent
lock=json.loads((r/'inputs.lock.json').read_text())
paths={'official-p54-modem.img.gz':'metadata/sb_rudolf_v1.01.85_single/modem-verified.img','eu25-donor.img.gz':'fullband_eu_bucket_order_fix_20mhz/modem.img','eu25-donor-manifest.json':'fullband_eu_bucket_order_fix_20mhz/manifest.json'}
for name,path in paths.items():assert hashlib.sha256((r/path).read_bytes()).hexdigest()==lock[name]['sha256'],path
subprocess.run([sys.executable,r/'build.py'],check=True)
sys.path.insert(0,str(r/'metadata'))
from audit_migration import sections
stock=sections((r/paths['official-p54-modem.img.gz']).read_bytes())['md1rom']['data']
out=sections((r/'build/modem-unsigned.img').read_bytes())['md1rom']['data']
for file in [0x1cd1294,0x1fe7fd0,0x20deb90]:assert stock[file-512:file-512+8]==out[file-512:file-512+8],hex(file)
report=json.loads((r/'build/report.json').read_text());assert not report['native_hooks'] and not report['device_authorization'] and not report['vendor_signed']
print('PASS pinned reference hashes, metadata build, stock runtime pointers, authorization-free unsigned report')
