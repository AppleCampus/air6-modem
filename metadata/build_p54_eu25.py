"""P54 full-CA-preserving metadata candidate. Preserve all original nodes; no flash."""
from pathlib import Path
import json,struct,hashlib
from audit_migration import sections,R,I,H
source=(R/'sb_rudolf_v1.01.85_single/modem-verified.img').read_bytes();assert H(source)=='6b6fbd2bae4dc073e60db1837f5b181a7f8a0b3d6c0c278de7cd91c057d31944'
p=sections(source);eu=sections((I/'fullband_eu_bucket_order_fix_20mhz/modem.img').read_bytes());regs=json.loads((R/'registry_comparison.json').read_text());graphs=json.loads((R/'nr_graph_inventory.json').read_text());spec=json.loads((R/'preserve_ca_metadata_plan.json').read_text());manifest=json.loads((I/'fullband_eu_bucket_order_fix_20mhz/manifest.json').read_text());inventory=json.loads((R/'migration_inventory.json').read_text());roots=json.loads((R/'metadata_root_candidates.json').read_text())
rom=bytearray(p['md1rom']['data'][:-512]);original_len=len(rom);drdi=bytearray(p['md1drdi']['data']);edits=[];objects=[];clones={};profiles=[]
def append(label,b):
 rom.extend(bytes(-len(rom)%4));at=len(rom);rom.extend(b);objects.append(dict(label=label,address=hex(0x90000000+at),bytes=len(b)));return 0x90000000+at
def edit(file,b,label):
 pos=file-512;assert 0<=pos and pos+len(b)<=original_len
 before=bytes(rom[pos:pos+len(b)]);rom[pos:pos+len(b)]=b;edits.append(dict(file=hex(file),old=before.hex(),new=bytes(b).hex(),label=label))
def row(g,idx):return next(x for x in regs if x['group']==g and x['index']==idx)
def oldread(idx,q,n):
 r=row(6,idx);base=int(r['old_target'],16);assert base<=q and q+n<=base+r['old_size'];s=int(r['old_source'],16)-0x50000000
 return eu['md1drdi']['data'][s+q-base:s+q-base+n]
def uroot(file):return struct.unpack_from('<I',eu['md1rom']['data'],file-512)[0]
def baseline_read(idx,q,n):
 for g in [6,5,7]:
  r=row(g,idx);base=int(r['new_target'],16);src=int(r['new_source'],16)-0x50000000
  if base<=q and q+n<=base+r['new_size']:return p['md1drdi']['data'][src+q-base:src+q-base+n]
 raise ValueError((idx,hex(q),n))
baseroot=lambda file:struct.unpack_from('<I',p['md1rom']['data'],file-512)[0]
donors=json.loads((R/'power_single_donors.json').read_text());powerroots=[]
for idx in [0,1]:
 r=row(6,idx);s=int(r['old_source'],16)-0x50000000;base=int(r['old_target'],16);blob=eu['md1drdi']['data'][s:s+r['old_size']]
 q=append(f'EU25 p{idx} metadata graph clone',blob);clones[idx]=q
 # Pointer-sized fields in these rooted graphs are word aligned. Values outside
 # this profile's exact loaded range (including other DRDI groups) stay intact.
 relocated=[]
 for at in range(0,len(blob)-3,4):
  v=struct.unpack_from('<I',blob,at)[0]
  if base<=v<base+len(blob):struct.pack_into('<I',rom,q-0x90000000+at,q+v-base);relocated.append(at)
 profiles.append(dict(profile=idx,clone=hex(q),source_bytes=len(blob),relocated_words=len(relocated),retained_P54_nodes=[]))
def relocated(idx,q):
 r=row(6,idx);base=int(r['old_target'],16);assert base<=q<base+r['old_size'];return clones[idx]+q-base
for idx in [0,1]:
 latest=next(x for x in graphs if x['version']=='P54' and x['profile']==idx);plan=spec['plans'][idx];n=plan['new_nodes'];donor_n=n-8;root=uroot(0x20012b0+idx*4);nodes=list(struct.unpack('<'+'I'*donor_n,oldread(idx,root,donor_n*4)))
 canonical_bands=[]
 for ptr in nodes:
  nd=struct.unpack('<4I',oldread(idx,ptr,16));info=struct.unpack('<4I',oldread(idx,nd[3],16));canonical_bands.append(oldread(idx,info[1],info[0]*4))
 canonical_bands.extend([None]*8)
 newnodes=[relocated(idx,q) for q in nodes]+[0]*8
 caps={}
 for direction,field in [('UL',0x20012e0),('DL',0x20012e8)]:
  vector=uroot(field+idx*4);values=[]
  for j in range(64):
   q=struct.unpack('<I',oldread(idx,vector+j*4,4))[0]
   if not q:break
   values.append(oldread(idx,q,4))
  assert values;caps[direction]=values
 # Extend these per-profile capability vectors with exact latest P54 values.
 for node in latest['nodes']:
  for mode,u,d in node['HW_resolved']:
   for direction,raw in [('UL',u),('DL',d)]:
    value=bytes.fromhex(raw)
    if value not in caps[direction]:caps[direction].append(value)
 caproots={}
 for direction in ['UL','DL']:
  pointers=[append(f'p{idx} {direction} capability {j}',value) for j,value in enumerate(caps[direction])]
  caproots[direction]=append(f'p{idx} {direction} capability vector',struct.pack('<'+'I'*(len(pointers)+1),*pointers,0))
 for oldindex,newindex in plan['old_to_new_index'].items():
  latest_node=latest['nodes'][int(oldindex)];bands=bytes.fromhex(latest_node['bands']);oldnode=tuple(latest_node['header'])
  canonical_bands[newindex]=bands
  hw=bytes(v for mode,u,d in latest_node['HW_resolved'] for v in [mode,caps['UL'].index(bytes.fromhex(u)),caps['DL'].index(bytes.fromhex(d))])
  hp=append(f'p{idx} preserved P54 node {oldindex} HW',hw);bp=append(f'p{idx} preserved P54 node {oldindex} band',bands)
  ip=append(f'p{idx} preserved P54 node {oldindex} info',struct.pack('<4I',len(bands)//4,bp,len(hw)//3,hp));np=append(f'p{idx} preserved P54 node {oldindex}',struct.pack('<4I',*oldnode[:3],ip))
  newnodes[newindex]=np
  profiles[idx]['retained_P54_nodes'].append(dict(old_index=int(oldindex),new_index=newindex,HW_records=len(hw)//3,bandhex=bands.hex(),HW_resolved_sha256=H(json.dumps(latest_node['HW_resolved'],separators=(',',':')).encode())))
 profiles[idx]['caproots']=caproots
 # Rebuild all ordinal-indexed parallel arrays. Copy retained P54 semantics,
 # not the old EU power array whose ordinals were not consistently remapped.
 assert all(newnodes) and all(canonical_bands)
 parallel={'CAP':append(f'p{idx} all P54 plus EU25 CAP vector',struct.pack('<'+'I'*(n+1),*newnodes,0))}
 for label,oldfield,newfield in [('SRS',0x2003030,0x2006178),('HPUE',0x2054bec,0x2057d34)]:
  src=uroot(oldfield+idx*4);array=[relocated(idx,q) if q else 0 for q in struct.unpack('<'+'I'*donor_n,oldread(idx,src,donor_n*4))]+[0]*8
  cache={}
  for oi,ni in plan['old_to_new_index'].items():
   q=struct.unpack('<I',baseline_read(idx,baseroot(newfield+idx*4)+int(oi)*4,4))[0]
   if not q:array[ni]=0;continue
   if q not in cache:
    if label=='HPUE':cache[q]=append(f'p{idx} latest HPUE {oi}',baseline_read(idx,q,3))
    else:
     obj=bytearray(baseline_read(idx,q,8));leaf=struct.unpack_from('<I',obj)[0]
     if leaf:struct.pack_into('<I',obj,0,append(f'p{idx} latest SRS leaf {oi}',baseline_read(idx,leaf,18)))
     cache[q]=append(f'p{idx} latest SRS {oi}',obj)
   array[ni]=cache[q]
  parallel[label]=append(f'p{idx} latest-preserving {label} ordinal vector',struct.pack('<'+'I'*n,*array))
 power=bytearray(n);retained=set(plan['old_to_new_index'].values());native_power=baseroot(0x21efa68+idx*4)
 for oi,ni in plan['old_to_new_index'].items():power[ni]=baseline_read(idx,native_power+int(oi),1)[0]
 proofs=[];cfg=baseroot(0x2057d2c+idx*4)
 for ni in range(n):
  if ni in retained:continue
  nd=struct.unpack('<4I',oldread(idx,nodes[ni],16));info=struct.unpack('<4I',oldread(idx,nd[3],16));assert info[0]==1
  band=oldread(idx,info[1],4).hex();matches=[v for v in donors[idx]['entries'] if v['bandhex']==band];assert len(matches)==1,(idx,ni,band,matches)
  entry=matches[0];group=entry['power_group'];cp=struct.unpack('<I',baseline_read(idx,cfg+group*4,4))[0];assert baseline_read(idx,cp,12).hex()==entry['config']
  power[ni]=group;proofs.append(dict(new_index=ni,**entry))
 powerroot=append(f'p{idx} corrected power ordinals',power);parallel['POWER']=powerroot;powerroots.append(powerroot)
 profiles[idx]['parallel_roots']=parallel;profiles[idx]['new_single_power_donors']=proofs;profiles[idx]['power_bytes']=power.hex()
 cc={17:0,0:1,2:2,3:3,4:4,5:5}
 def key(j):
  b=canonical_bands[j];nb=len(b)//4;dl=sum(cc[b[j+3]] for j in range(0,len(b),4));ul=sum(cc[b[j+2]] for j in range(0,len(b),4));uln=sum(b[j+2]!=17 for j in range(0,len(b),4));return dl<<12|nb<<8,ul<<12|uln<<8
 order=sorted(range(n),key=lambda j:(key(j),j));groups=[]
 for pos,j in enumerate(order):
  k=key(j)
  if not groups or tuple(groups[-1][:2])!=k:groups.append([*k,pos])
 parallel['REMAP']=append(f'p{idx} regenerated group permutation',struct.pack('<'+'H'*n,*order));parallel['GROUPS']=append(f'p{idx} regenerated group starts',b''.join(struct.pack('<3I',*g) for g in groups));profiles[idx]['groups']=groups
# Exact table pair ordering, derived from paired native export arrays. A pair
# at 2001320/2001328 is interleaved with its scalar size fields.
for pair in range(0,len(roots),2):
 for idx,root in enumerate(roots[pair:pair+2]):
  oldfile=int(root['old_file'],16);c=root['candidates']
  if len(c)==1:newfile=int(c[0]['new_file'],16)
  else:
   delta=0x3048;assert oldfile in [0x21ec72c,0x21ec730,0x21ec734,0x21ec738,0x21eca10,0x21eca14,0x21eca18];newfile=oldfile+delta
  value=uroot(oldfile);newvalue=relocated(idx,value)
  if oldfile==0x20012e0+idx*4:newvalue=profiles[idx]['caproots']['UL']
  if oldfile==0x20012e8+idx*4:newvalue=profiles[idx]['caproots']['DL']
  for field,label in [(0x20012b0,'CAP'),(0x2003030,'SRS'),(0x2054bec,'HPUE'),(0x21eca20,'POWER'),(0x21ec72c,'REMAP'),(0x21ec734,'GROUPS')]:
   if oldfile==field+idx*4:newvalue=profiles[idx]['parallel_roots'][label]
  edit(newfile,struct.pack('<I',newvalue),f'p{idx} rooted G6 export from {hex(oldfile)}')
power_vector=append('P54 power setter pointer vector',struct.pack('<2I',*powerroots));at=0x141b11a-512;h,imm=struct.unpack_from('<HI',rom,at);assert h==0x60e3 and (0x90000000+at+6+imm)&0xffffffff==0x2424aca8
edit(at+512,struct.pack('<HI',h,(power_vector-(0x90000000+at+6))&0xffffffff),'P54 power DRDI setter source; corrected ordinal vector')
# Apply only old RF/LTE changes whose native groups are byte-identical at the
# edited spans. Never replace the whole P54 DRDI, preserving its version data.
rf_edits=[]
for patch in manifest['patches']:
 file=int(patch['offset'],16);before=bytes.fromhex(patch['old']);after=bytes.fromhex(patch['new'])
 if file<0x223ee40:continue
 offset=file-0x223ee40
 owners=[r for r in regs if int(r['old_source'],16)-0x50000000<=offset and offset+len(before)<=int(r['old_source'],16)-0x50000000+r['old_size']]
 assert len(owners)==1
 r=owners[0]
 if r['group']==6:continue
 assert r['group'] in [5,7,8,9]
 at=int(r['new_source'],16)-0x50000000+offset-(int(r['old_source'],16)-0x50000000)
 assert drdi[at:at+len(before)]==before,(r['group'],r['index'],patch['offset'])
 drdi[at:at+len(before)]=after;rf_edits.append(dict(old_file=patch['offset'],new_drdi_offset=hex(at),bytes=len(before),group=r['group'],profile=r['index']))
# Changed physical CDF roots can point into the old EU G6 donor cavity. The
# latest P54 loaded G6 is deliberately preserved, so those roots must use the
# relocated donor clone as well. Comparing bytes, rather than a group-only
# patch inventory, exposes these cross-group dependencies.
cdf_relocations=[]
for idx in [0,1]:
 g6=row(6,idx);base=int(g6['old_target'],16);size=g6['old_size']
 for group in [5,7]:
  owner=row(group,idx);src=int(owner['new_source'],16)-0x50000000
  for off in range(0,owner['new_size']-3,4):
   at=src+off;value=struct.unpack_from('<I',drdi,at)[0]
   original=struct.unpack_from('<I',p['md1drdi']['data'],at)[0]
   if value==original or not base<=value<base+size:continue
   target=relocated(idx,value);struct.pack_into('<I',drdi,at,target)
   cdf_relocations.append(dict(profile=idx,group=group,drdi_offset=hex(at),source=hex(value),target=hex(target),original=hex(original)))
assert len(cdf_relocations)==32 and [sum(x['profile']==i for x in cdf_relocations) for i in [0,1]]==[13,19],cdf_relocations
# Band-list and power-count edits with unique original contexts.
for oldfile in [0x1de3e18,0x1dfb754,0x1ef1aac,0x2054b18,0x2054b7e,0x2160614]:
 patch=next(x for x in manifest['patches'] if int(x['offset'],16)==oldfile);match=next(x for x in inventory['EU_patches'] if int(x['old_offset'],16)==oldfile)
 if match['unique_32byte_context']:newfile=int(match['new_file_offset'],16)
 else:
  assert oldfile==0x2054b7e;newfile=oldfile+0x3148
 before=bytes.fromhex(patch['old']);assert rom[newfile-512:newfile-512+len(before)]==before
 edit(newfile,bytes.fromhex(patch['new']),f'EU25 pinned logical change {hex(oldfile)}')
edit(0x2004412,struct.pack('<H',74),'MAXCOMB74 all original CA retained');edit(0x2004415,b'\x0d','13 NR singles')
for idx in [0,1]:edit(0x20043e4+idx*2,struct.pack('<H',len(profiles[idx]['groups'])),'Recomputed NR group count')
# Nine native array references require independently assembled relocation evidence.
# This draft deliberately stops before emission until that evidence is supplied.
state=dict(status='P54_ROOTED_METADATA_DRAFT_PENDING_BSS_REBASE_AND_INDEPENDENT_AUDIT',flash_eligible=False,source_sha256=H(source),profiles=profiles,CDF_cross_group_relocations=cdf_relocations,ROM_edits=edits,RF_edits=rf_edits,objects=objects,ROM_bytes_without_tail=len(rom),DRDI_sha256=H(drdi),limits=['Original P54 retained-node HW preserved semantically','Added-band donor records remain hypotheses requiring board/network validation','No image emitted until nine BSS references and reserved memory layout are verified'])
(R/'eu25_metadata_draft.json').write_text(json.dumps(state,indent=2));(R/'draft_rom_without_tail.bin').write_bytes(rom);(R/'draft_drdi.bin').write_bytes(drdi);print('DRAFT',len(rom),len(edits),len(rf_edits))
