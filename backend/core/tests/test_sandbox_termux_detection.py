from backend.core.routers import sandbox


def test_is_termux_android_detects_prefix(monkeypatch):
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    monkeypatch.delenv("ANDROID_ROOT", raising=False)
    assert sandbox._is_termux_android() is True


def test_is_termux_android_detects_android_root(monkeypatch):
    monkeypatch.delenv("PREFIX", raising=False)
    monkeypatch.setenv("ANDROID_ROOT", "/system")
    assert sandbox._is_termux_android() is True


def test_is_termux_android_false_elsewhere(monkeypatch):
    monkeypatch.setenv("PREFIX", "/usr/local")
    monkeypatch.delenv("ANDROID_ROOT", raising=False)
    assert sandbox._is_termux_android() is False
