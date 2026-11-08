from pathlib import Path
import hashlib,struct
R=Path(__file__).resolve().parent;I=R.parent
H=lambda b:hashlib.sha256(b).hexdigest()
def sections(d):
 p=0;out={}
 while p+80<=len(d) and struct.unpack_from('<I',d,p)[0]==0x58881688:
  n=struct.unpack_from('<I',d,p+4)[0];h=struct.unpack_from('<I',d,p+52)[0];a=struct.unpack_from('<I',d,p+68)[0]
  assert h==512 and a==16 and p+h+n<=len(d)
  name=d[p+8:p+40].split(b'\0')[0].decode();assert name not in out
  if name in ['md1rom','md1drdi']:out[name]=dict(file=p+h,header=d[p:p+h],data=d[p+h:p+h+n])
  p+=h+n+(-n%a)
 assert set(out)=={'md1rom','md1drdi'}
 return out
