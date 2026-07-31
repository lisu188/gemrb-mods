#!/usr/bin/env python3
from pathlib import Path
import py_compile
ROOT=Path(__file__).resolve().parents[1]

def rows(name):
    data=(ROOT/'tables'/name).read_text().splitlines()
    return [line.split() for line in data[3:] if line.strip() and not line.lstrip().startswith(('#','//'))]

def main():
    pool=rows('psionpool.2da'); known=rows('psionknown.2da'); powers=rows('psionpowers.2da')
    assert len(pool)==20 and len(known)==20
    assert [int(r[2]) for r in powers].count(1)==12
    assert len(powers)==60
    refs={r[0] for r in powers}
    import re
    clab=(ROOT/'tables'/'clabpsio.2da').read_text()
    learned=set(re.findall(r'GA_(PS[0-9A-Z]+)', clab))
    assert learned <= refs
    setup=(ROOT/'setup-psion.tp2').read_text()
    for table in ('psionpool','psionknown','psiondisc','psionskills','psionfeats','psionpowers','mxpsion','clabpsio'):
        assert table in setup
    for inc in ('class-detect.tpa','class-strings.tpa','class-layout.tpa','class-common.tpa','class-skills.tpa'):
        assert inc in setup
    py_compile.compile(str(ROOT/'guiscripts'/'Psionics.py'),doraise=True)
    py_compile.compile(str(ROOT/'tools'/'install_guiscripts.py'),doraise=True)
    print('Psion alpha static validation passed.')
if __name__=='__main__': main()
