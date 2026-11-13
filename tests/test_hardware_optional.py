"""Opt-in tests; never run real applications in the ordinary software test suite."""
import os,sys
from pathlib import Path
import pytest
@pytest.mark.skipif(os.name!='nt' or os.environ.get('IDCS_HARDWARE_TEST')!='1',reason='Requires explicit Windows hardware test opt-in')
def test_real_coreldraw21(tmp_path):
    sys.path.insert(0,str(Path('windows-agent').resolve()))
    from coreldraw.adapter import CorelAdapter
    with CorelAdapter() as corel:
        result=corel.diagnostic(tmp_path)
        assert result['version']==21 and result['cdr'] and result['pdf']
