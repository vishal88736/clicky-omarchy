from pathlib import Path
import pytest
from clicky.install import install,uninstall


def test_install_uninstall_restores_config_and_preserves_later_edits(tmp_path):
    bindings=tmp_path/'.config/hypr/bindings.lua';bindings.parent.mkdir(parents=True)
    original=b'-- original configuration without final newline';bindings.write_bytes(original)
    result=install(tmp_path,activate=False);assert result['installed']
    assert original in bindings.read_bytes()
    bindings.write_bytes(bindings.read_bytes()+b'-- later user edit\n')
    with pytest.raises(ValueError,match='Already installed'):install(tmp_path,activate=False)
    result=uninstall(tmp_path,activate=False);assert result['history_retained']
    assert bindings.read_bytes()==original+b'-- later user edit\n'
    assert not (tmp_path/'.local/bin/clicky').exists()
    assert Path(result['backup_retained']).read_bytes()==original


def test_uninstall_refuses_modified_owned_files(tmp_path):
    install(tmp_path,activate=False);launcher=tmp_path/'.local/bin/clicky';launcher.write_text('user modification')
    before=(tmp_path/'.config/hypr/bindings.lua').read_bytes()
    with pytest.raises(ValueError,match='Owned file changed'):uninstall(tmp_path,activate=False)
    assert launcher.read_text()=='user modification'
    assert (tmp_path/'.config/hypr/bindings.lua').read_bytes()==before
