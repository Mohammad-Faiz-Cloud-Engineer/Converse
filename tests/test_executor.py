import pytest

from converse.executor import (
    determine_risk_level,
    check_blocked,
    run_command,
    _strip_sudo,
    RiskLevel,
)


class TestStripSudo:
    def test_with_sudo(self):
        cmd, had = _strip_sudo("sudo rm -rf /")
        assert had is True
        assert cmd == "rm -rf /"

    def test_without_sudo(self):
        cmd, had = _strip_sudo("ls -la")
        assert had is False
        assert cmd == "ls -la"

    def test_multiple_sudo(self):
        cmd, had = _strip_sudo("sudo sudo echo hi")
        assert had is True
        assert cmd == "sudo echo hi"

    def test_sudo_in_middle(self):
        cmd, had = _strip_sudo("echo sudo test")
        assert had is False
        assert cmd == "echo sudo test"

    def test_empty(self):
        cmd, had = _strip_sudo("")
        assert had is False
        assert cmd == ""


class TestDetermineRiskLevel:
    @pytest.mark.parametrize("cmd", [
        "ls", "ls -la", "pwd", "echo hello", "cat file.txt",
        "head -20 log.txt", "tail -f log.txt", "grep foo bar.txt",
        "find . -name '*.py'", "which python3", "whoami", "id",
        "uname -a", "date", "uptime", "ps aux", "df -h",
        "env", "history", "alias", "git status", "git diff",
        "python3 --version", "man ls", "whatis ls",
    ])
    def test_low_risk(self, cmd):
        assert determine_risk_level(cmd) == RiskLevel.LOW, f"{cmd} should be LOW"

    @pytest.mark.parametrize("cmd", [
        "mkdir test", "touch file.txt", "cp a b", "mv a b",
        "rm test.txt", "sudo rm test.txt",
        "nano file.txt", "vim file.txt", "code .",
        "curl https://example.com", "wget https://example.com",
        "tar -czf archive.tar.gz dir", "gzip file", "zip archive.zip file",
        "pip install requests", "npm install express",
        "apt-get update", "brew install python",
        "sudo mkdir /opt/test", "sudo touch /tmp/x",
    ])
    def test_medium_risk(self, cmd):
        assert determine_risk_level(cmd) == RiskLevel.MEDIUM, f"{cmd} should be MEDIUM got {determine_risk_level(cmd)}"

    @pytest.mark.parametrize("cmd", [
        "rm -rf /tmp/test", "rm --recursive /tmp/x",
        "sudo rm -rf /", "kill 1234", "pkill firefox",
        "killall chrome", "chmod 777 script.sh",
        "chown user:user file.txt", "docker rm container",
        "docker rmi image", "git reset --hard HEAD",
        "git clean -fd", "git push --force",
    ])
    def test_high_risk(self, cmd):
        assert determine_risk_level(cmd) == RiskLevel.HIGH, f"{cmd} should be HIGH got {determine_risk_level(cmd)}"

    @pytest.mark.parametrize("cmd", [
        "reboot", "shutdown -h now", "poweroff", "halt",
        "sudo reboot", "sudo shutdown -h now",
        "apt remove package", "apt-get purge package",
        "dpkg --remove package", "rpm -e package",
        "pacman -R package", "dd if=/dev/zero of=/dev/sda",
        "mkfs.ext4 /dev/sda1", "fdisk /dev/sda",
        "parted /dev/sda",
    ])
    def test_critical_risk(self, cmd):
        assert determine_risk_level(cmd) == RiskLevel.CRITICAL, f"{cmd} should be CRITICAL got {determine_risk_level(cmd)}"

    def test_sudo_escalation(self):
        assert determine_risk_level("sudo echo hello") == RiskLevel.MEDIUM
        assert determine_risk_level("sudo cat /etc/shadow") == RiskLevel.MEDIUM

    def test_empty_string(self):
        assert determine_risk_level("") == RiskLevel.LOW
        assert determine_risk_level("   ") == RiskLevel.LOW

    def test_plain_rm_is_medium(self):
        assert determine_risk_level("rm file.txt") == RiskLevel.MEDIUM
        assert determine_risk_level("rm -f file.txt") == RiskLevel.HIGH

    def test_rm_rf_is_high(self):
        assert determine_risk_level("rm -rf /tmp") == RiskLevel.HIGH
        assert determine_risk_level("rm -rf") == RiskLevel.HIGH
        assert determine_risk_level("rm -fr /tmp") == RiskLevel.HIGH


class TestCheckBlocked:
    def test_word_boundary_prevents_false_positive(self):
        blocked = ["rm"]
        assert check_blocked("mkdir test", blocked) is None
        assert check_blocked("firmware update", blocked) is None
        assert check_blocked("rmdir dir", blocked) is None
        assert check_blocked("arm file", blocked) is None

    def test_word_boundary_matches_correctly(self):
        blocked = ["rm"]
        assert check_blocked("rm -rf /", blocked) is not None
        assert check_blocked("rm file.txt", blocked) is not None
        assert check_blocked("/usr/bin/rm file", blocked) is not None
        assert check_blocked("sudo rm file", blocked) is not None

    def test_multi_word_blocked_command(self):
        blocked = ["rm -rf"]
        assert check_blocked("rm -rf /tmp", blocked) is not None
        assert check_blocked("sudo rm -rf /", blocked) is not None
        assert check_blocked("rm file.txt", blocked) is None

    def test_pattern_with_special_chars_falls_back_to_substring(self):
        blocked = ["rm (.*)"]
        assert check_blocked("rm (.*) file", blocked) is not None
        assert check_blocked("rm file", blocked) is None

    def test_leading_non_word_pattern(self):
        blocked = ["/usr/bin/rm"]
        assert check_blocked("/usr/bin/rm file", blocked) is not None
        assert check_blocked("rm file", blocked) is None

    def test_multiple_blocked_commands(self):
        blocked = ["reboot", "shutdown"]
        assert check_blocked("shutdown -h now", blocked) is not None
        assert check_blocked("reboot", blocked) is not None
        assert check_blocked("systemctl restart", blocked) is None
        assert check_blocked("ls", blocked) is None

    def test_empty_blocked_list(self):
        assert check_blocked("rm -rf /", []) is None

    def test_empty_command(self):
        assert check_blocked("", ["rm"]) is None

    def test_case_insensitive(self):
        blocked = ["RM -RF"]
        assert check_blocked("rm -rf /", blocked) is not None
        assert check_blocked("RM -RF /", blocked) is not None

    def test_blocked_reboot_does_not_match_rebooting(self):
        blocked = ["reboot"]
        assert check_blocked("rebooting the system", blocked) is None
        assert check_blocked("reboot", blocked) is not None


class TestRunCommand:
    def test_simple_command(self):
        result = run_command("echo hello")
        assert result.returncode == 0

    def test_failing_command(self):
        result = run_command("false")
        assert result.returncode != 0

    def test_command_with_output(self):
        result = run_command("echo test_output")
        assert result.returncode == 0
