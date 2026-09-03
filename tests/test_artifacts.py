from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import pytest

from hashoej_document_builder.core.artifacts import ArtifactManager


def test_artifact_manager_create_path(tmp_path: Path) -> None:
    manager = ArtifactManager(temp_root=tmp_path / "artifacts")
    docx_path = manager.create_artifact_path("docx")

    assert docx_path.name == "document.docx"
    assert docx_path.parent.name.startswith("art_")
    assert docx_path.parent.parent == (tmp_path / "artifacts").resolve()
    assert docx_path.parent.is_dir()


def test_artifact_manager_invalid_formats_and_prefixes_rejected(tmp_path: Path) -> None:
    manager = ArtifactManager(temp_root=tmp_path / "artifacts")

    # Invalid file formats
    with pytest.raises(ValueError, match="Unsupported artifact file format 'exe'"):
        manager.create_artifact_path("exe")
    with pytest.raises(ValueError, match="Unsupported artifact file format 'sh'"):
        manager.create_artifact_path("sh")
    with pytest.raises(ValueError, match="Unsupported artifact file format 'txt'"):
        manager.create_artifact_path("txt")

    # Invalid prefixes (directory traversal, path separators, illegal chars)
    with pytest.raises(ValueError, match="Invalid artifact prefix"):
        manager.create_artifact_path("docx", prefix="../../bad")
    with pytest.raises(ValueError, match="Invalid artifact prefix"):
        manager.create_artifact_path("docx", prefix="art/nested")
    with pytest.raises(ValueError, match="Invalid artifact prefix"):
        manager.create_artifact_path("docx", prefix="art\\nested")
    with pytest.raises(ValueError, match="Invalid artifact prefix"):
        manager.create_artifact_path("docx", prefix="too_long_prefix_1234567890")


def test_artifact_manager_stale_cleanup_boundary(tmp_path: Path) -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    def clock():
        return now

    root = tmp_path / "artifacts"
    manager = ArtifactManager(temp_root=root, ttl_minutes=10, now_fn=clock)

    # Create 3 artifacts
    path_9m59s = manager.create_artifact_path("docx", prefix="art1")
    path_10m0s = manager.create_artifact_path("docx", prefix="art2")
    path_10m1s = manager.create_artifact_path("docx", prefix="art3")

    path_9m59s.write_bytes(b"content 1")
    path_10m0s.write_bytes(b"content 2")
    path_10m1s.write_bytes(b"content 3")

    # 1. Set mtime for 9m 59s ago (599s old < 600s TTL) -> FRESH (retained)
    mtime_9m59s = (now - timedelta(seconds=599)).timestamp()
    os.utime(path_9m59s.parent, (mtime_9m59s, mtime_9m59s))
    os.utime(path_9m59s, (mtime_9m59s, mtime_9m59s))

    # 2. Set mtime for exactly 10m 0s ago (600s old == 600s TTL) -> STALE (removed by <= boundary)
    mtime_10m0s = (now - timedelta(seconds=600)).timestamp()
    os.utime(path_10m0s.parent, (mtime_10m0s, mtime_10m0s))
    os.utime(path_10m0s, (mtime_10m0s, mtime_10m0s))

    # 3. Set mtime for 10m 1s ago (601s old > 600s TTL) -> STALE (removed)
    mtime_10m1s = (now - timedelta(seconds=601)).timestamp()
    os.utime(path_10m1s.parent, (mtime_10m1s, mtime_10m1s))
    os.utime(path_10m1s, (mtime_10m1s, mtime_10m1s))

    purged = manager.cleanup_stale_artifacts()
    assert purged == 2

    # Exactly 10m0s and 10m1s are removed; 9m59s is retained
    assert path_9m59s.parent.exists()
    assert not path_10m0s.parent.exists()
    assert not path_10m1s.parent.exists()


def test_artifact_cleanup_sibling_prefix_attack_protection(tmp_path: Path) -> None:
    """Ensure paths like /tmp/artifacts_backup cannot be accessed through /tmp/artifacts."""
    root = tmp_path / "artifacts"
    sibling_root = tmp_path / "artifacts_backup"
    sibling_root.mkdir()

    sibling_file = sibling_root / "important.docx"
    sibling_file.write_bytes(b"critical secret backup")

    manager = ArtifactManager(temp_root=root)

    # Explicit cleanup targeting sibling
    assert manager.cleanup_artifact(sibling_file) is False
    assert manager.cleanup_artifact(sibling_root) is False

    # Sibling remains intact
    assert sibling_file.is_file()
    assert sibling_file.read_bytes() == b"critical secret backup"


def test_artifact_cleanup_symlink_escape_protection(tmp_path: Path) -> None:
    """Symlinks inside temp_root pointing outside must never cause external target deletion."""
    root = tmp_path / "artifacts"
    root.mkdir()

    outside_dir = tmp_path / "external_target_dir"
    outside_dir.mkdir()
    outside_file = outside_dir / "target.txt"
    outside_file.write_text("should remain safe", encoding="utf-8")

    # Create symlink inside artifacts pointing to external dir
    symlink_dir = root / "art_symlink"
    symlink_dir.symlink_to(outside_dir, target_is_directory=True)

    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    manager = ArtifactManager(temp_root=root, now_fn=lambda: now)

    # Set symlink timestamp to stale
    stale_time = (now - timedelta(minutes=15)).timestamp()
    os.utime(symlink_dir, (stale_time, stale_time), follow_symlinks=False)

    purged = manager.cleanup_stale_artifacts()
    assert purged == 1

    # Symlink inside root was removed
    assert not symlink_dir.is_symlink()
    assert not symlink_dir.exists()

    # External target directory and file remain completely intact!
    assert outside_dir.is_dir()
    assert outside_file.is_file()
    assert outside_file.read_text(encoding="utf-8") == "should remain safe"


def test_artifact_manager_explicit_cleanup(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    manager = ArtifactManager(temp_root=root)

    art_path = manager.create_artifact_path("docx")
    art_path.write_bytes(b"temp docx")
    parent_dir = art_path.parent

    assert art_path.is_file()
    assert manager.cleanup_artifact(art_path) is True
    assert not art_path.exists()
    assert not parent_dir.exists()
