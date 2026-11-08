#!/usr/bin/env python3
"""Build unsigned metadata-only modem research output from external reference inputs."""
import subprocess,sys
from pathlib import Path
if not __debug__:raise SystemExit('Do not disable assertions')
r=Path(__file__).resolve().parent
for name in ['build_p54_eu25.py','emit_unsigned.py']:
 subprocess.run([sys.executable,r/'metadata'/name],check=True)
