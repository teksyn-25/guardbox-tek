"""
Hardening configuration tests.

Validates that docker-compose.yml, seccomp-profile.json, and Dockerfile
enforce the required security constraints. These are static config checks —
they catch regressions if someone accidentally relaxes a security setting.
"""

import json
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).parent.parent
_SECCOMP = _ROOT / "seccomp-profile.json"
_COMPOSE = _ROOT / "docker-compose.yml"
_DOCKERFILE = _ROOT / "backend" / "Dockerfile"


# ── seccomp profile ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def seccomp() -> dict:
    return json.loads(_SECCOMP.read_text())


@pytest.fixture(scope="module")
def blocked_syscalls(seccomp) -> set[str]:
    denied = set()
    for rule in seccomp.get("syscalls", []):
        if rule.get("action") == "SCMP_ACT_ERRNO":
            denied.update(rule["names"])
    return denied


def test_seccomp_profile_exists():
    assert _SECCOMP.exists(), "seccomp-profile.json missing"


def test_seccomp_profile_is_valid_json():
    data = json.loads(_SECCOMP.read_text())
    assert isinstance(data, dict)


def test_seccomp_default_action_is_allow(seccomp):
    assert seccomp["defaultAction"] == "SCMP_ACT_ALLOW"


def test_seccomp_blocks_ptrace(blocked_syscalls):
    assert "ptrace" in blocked_syscalls


def test_seccomp_blocks_cross_process_memory(blocked_syscalls):
    assert "process_vm_readv" in blocked_syscalls
    assert "process_vm_writev" in blocked_syscalls


def test_seccomp_blocks_kernel_module_ops(blocked_syscalls):
    assert "init_module" in blocked_syscalls
    assert "finit_module" in blocked_syscalls
    assert "delete_module" in blocked_syscalls


def test_seccomp_blocks_kexec(blocked_syscalls):
    assert "kexec_load" in blocked_syscalls
    assert "kexec_file_load" in blocked_syscalls


def test_seccomp_blocks_bpf(blocked_syscalls):
    assert "bpf" in blocked_syscalls


def test_seccomp_blocks_perf_event(blocked_syscalls):
    assert "perf_event_open" in blocked_syscalls


def test_seccomp_blocks_keyring(blocked_syscalls):
    assert "add_key" in blocked_syscalls
    assert "keyctl" in blocked_syscalls
    assert "request_key" in blocked_syscalls


def test_seccomp_blocks_mount(blocked_syscalls):
    assert "mount" in blocked_syscalls
    assert "umount2" in blocked_syscalls


def test_seccomp_blocks_namespace_manipulation(blocked_syscalls):
    assert "unshare" in blocked_syscalls
    assert "setns" in blocked_syscalls


def test_seccomp_blocks_chroot(blocked_syscalls):
    assert "chroot" in blocked_syscalls


def test_seccomp_blocks_reboot(blocked_syscalls):
    assert "reboot" in blocked_syscalls


# ── docker-compose ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(_COMPOSE.read_text())


@pytest.fixture(scope="module")
def api_service(compose) -> dict:
    return compose["services"]["api"]


def test_compose_no_frontend_service(compose):
    assert "frontend" not in compose["services"]


def test_compose_api_binds_localhost_only(api_service):
    ports = api_service.get("ports", [])
    for p in ports:
        assert str(p).startswith("127.0.0.1:"), f"port {p!r} is not localhost-only"


def test_compose_api_has_cap_drop_all(api_service):
    assert "ALL" in api_service.get("cap_drop", [])


def test_compose_api_has_no_new_privileges(api_service):
    opts = api_service.get("security_opt", [])
    assert "no-new-privileges:true" in opts


def test_compose_api_references_seccomp_profile(api_service):
    opts = api_service.get("security_opt", [])
    assert any("seccomp:" in o for o in opts)


def test_compose_api_has_read_only_rootfs(api_service):
    assert api_service.get("read_only") is True


def test_compose_api_has_tmpfs(api_service):
    tmpfs = api_service.get("tmpfs", [])
    assert any("/tmp" in t for t in tmpfs)


def test_compose_api_has_data_volume(api_service):
    volumes = api_service.get("volumes", [])
    assert any("guardbox_data" in str(v) for v in volumes)


# ── Dockerfile ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def dockerfile_text() -> str:
    return _DOCKERFILE.read_text()


def test_dockerfile_runs_as_nonroot(dockerfile_text):
    assert "USER guardbox" in dockerfile_text


def test_dockerfile_creates_system_user(dockerfile_text):
    assert "useradd --system" in dockerfile_text


def test_dockerfile_user_has_no_login_shell(dockerfile_text):
    assert "nologin" in dockerfile_text


def test_dockerfile_no_ssh_or_sudo(dockerfile_text):
    assert "ssh" not in dockerfile_text.lower()
    assert "sudo" not in dockerfile_text.lower()
