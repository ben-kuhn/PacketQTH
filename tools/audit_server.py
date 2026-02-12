#!/usr/bin/env python3
"""
PacketQTH Server Security Audit

Performs comprehensive security audit of the server module (telnet & session).
"""

import re
import sys
from pathlib import Path


class ServerSecurityAudit:
    """Security audit for server module."""

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
        self.files_audited = []

    def issue(self, severity, category, message, file=None, line=None, recommendation=None):
        """Record a security issue."""
        self.issues.append({
            'severity': severity,
            'category': category,
            'message': message,
            'file': file,
            'line': line,
            'recommendation': recommendation
        })

    def warning(self, category, message, file=None):
        """Record a warning."""
        self.warnings.append({
            'category': category,
            'message': message,
            'file': file
        })

    def success(self, category, message):
        """Record a passed check."""
        self.passed.append({
            'category': category,
            'message': message
        })

    def audit_file(self, filepath):
        """Audit a single file."""
        with open(filepath, 'r') as f:
            code = f.read()
            lines = code.split('\n')

        filename = Path(filepath).name
        self.files_audited.append(filename)

        print(f"Auditing: {filename}")
        print("-" * 70)

        # Network Security Checks
        self._check_network_security(code, filename, lines)

        # Input Validation Checks
        self._check_input_validation(code, filename, lines)

        # Resource Management Checks
        self._check_resource_management(code, filename, lines)

        # Error Handling Checks
        self._check_error_handling(code, filename, lines)

        # Code Security Checks
        self._check_code_security(code, filename, lines)

        # DoS Protection Checks
        self._check_dos_protection(code, filename, lines)

        print()

    def _check_network_security(self, code, filename, lines):
        """Check network security."""
        # Check for IP validation
        if 'ip_safelist' in code or 'ip_allowlist' in code:
            self.success('Network Security', f'{filename}: IP safelist implemented')
        else:
            if 'telnet' in filename.lower():
                self.warning('Network Security',
                           f'{filename}: No IP safelist detected', filename)

        # Check for CIDR support
        if 'ipaddress' in code and 'ip_network' in code:
            self.success('Network Security', f'{filename}: CIDR notation support')

        # Check for connection limits
        if 'max_connections' in code or 'max_clients' in code:
            self.success('Network Security', f'{filename}: Connection limits implemented')
        else:
            if 'server' in filename.lower():
                self.issue('MEDIUM', 'Network Security',
                          f'{filename}: No connection limit detected',
                          filename, None,
                          'Implement max_connections to prevent resource exhaustion')

        # Check for timeout configuration
        if 'timeout' in code.lower():
            self.success('Network Security', f'{filename}: Timeout mechanism present')
        else:
            self.warning('Network Security',
                       f'{filename}: No timeout configuration detected', filename)

        # Check for TLS/SSL (expected to be absent for packet radio)
        if 'ssl' in code.lower() or 'tls' in code.lower():
            self.warning('Network Security',
                       f'{filename}: SSL/TLS detected (may not be amateur radio compliant)',
                       filename)

    def _check_input_validation(self, code, filename, lines):
        """Check input validation."""
        # Check for input sanitization
        if re.search(r'\.strip\(\)|\.upper\(\)|\.lower\(\)', code):
            self.success('Input Validation', f'{filename}: Input normalization present')

        # Check for length limits
        if 'readline' in code:
            # Check if readline has a limit
            if re.search(r'readline\([^)]*\d+', code):
                self.success('Input Validation',
                           f'{filename}: Input length limits on readline')
            else:
                self.warning('Input Validation',
                           f'{filename}: readline without explicit length limit', filename)

        # Check for command injection protection
        if re.search(r'os\.system|subprocess|shell=True', code):
            self.issue('CRITICAL', 'Input Validation',
                      f'{filename}: Potential command injection via os.system/subprocess',
                      filename, None,
                      'Never use shell=True with user input')

        # Check for SQL injection (unlikely but check)
        if re.search(r'execute.*%s|execute.*\+.*input', code):
            self.issue('HIGH', 'Input Validation',
                      f'{filename}: Potential SQL injection',
                      filename, None,
                      'Use parameterized queries')

        # Check for path traversal
        if 'open(' in code and 'input' in code.lower():
            self.warning('Input Validation',
                       f'{filename}: File operations with potential user input', filename)

    def _check_resource_management(self, code, filename, lines):
        """Check resource management."""
        # Check for connection cleanup
        if 'close()' in code or 'wait_closed()' in code:
            self.success('Resource Management', f'{filename}: Connection cleanup present')

        # Check for memory limits
        if 'maxsize' in code or 'max_size' in code:
            self.success('Resource Management', f'{filename}: Size limits configured')

        # Check for file descriptor limits
        if 'max_connections' in code:
            self.success('Resource Management',
                       f'{filename}: Connection limits (prevents FD exhaustion)')

        # Check for async context managers
        if 'async with' in code:
            self.success('Resource Management',
                       f'{filename}: Async context managers (proper cleanup)')

        # Check for exception handling in cleanup
        if re.search(r'finally:.*close|except.*close', code, re.DOTALL):
            self.success('Resource Management',
                       f'{filename}: Cleanup in exception handlers')

    def _check_error_handling(self, code, filename, lines):
        """Check error handling for information disclosure."""
        # Check for exception exposure
        if re.search(r'except.*as\s+\w+:', code) and re.search(r'print.*\w+|log.*\w+|send.*\w+', code):
            self.warning('Information Disclosure',
                       f'{filename}: Check exception handling for information leaks', filename)

        # Check for generic error messages
        if 'ERR:' in code or 'Error:' in code:
            self.success('Error Handling', f'{filename}: Error message formatting present')

        # Check for stack trace exposure
        if 'traceback' in code:
            self.warning('Information Disclosure',
                       f'{filename}: Traceback usage detected - review for exposure',
                       filename)

        # Check for logging levels
        if re.search(r'logger\.debug|logger\.info', code):
            self.success('Error Handling', f'{filename}: Appropriate logging levels')

    def _check_code_security(self, code, filename, lines):
        """Check general code security."""
        # Check for eval/exec
        if re.search(r'\beval\s*\(|\bexec\s*\(', code):
            self.issue('CRITICAL', 'Code Injection',
                      f'{filename}: Use of eval() or exec() detected',
                      filename, None,
                      'Remove eval/exec - use safer alternatives')
        else:
            self.success('Code Security', f'{filename}: No eval/exec usage')

        # Check for pickle
        if 'pickle' in code:
            self.issue('MEDIUM', 'Deserialization',
                      f'{filename}: Pickle usage detected',
                      filename, None,
                      'Avoid pickle for untrusted data')
        else:
            self.success('Code Security', f'{filename}: No pickle usage')

        # Check for hardcoded credentials
        if re.search(r'password\s*=\s*["\'][^"\']+["\']|secret\s*=\s*["\'][^"\']+["\']',
                    code, re.IGNORECASE):
            matches = re.findall(r'password\s*=\s*["\'][^"\']+["\']|secret\s*=\s*["\'][^"\']+["\']',
                                code, re.IGNORECASE)
            for match in matches:
                if 'example' not in match.lower() and 'test' not in match.lower():
                    self.warning('Secrets',
                               f'{filename}: Potential hardcoded secret', filename)

        # Check for type checking
        if 'isinstance' in code or 'type(' in code:
            self.success('Code Security', f'{filename}: Type checking present')

    def _check_dos_protection(self, code, filename, lines):
        """Check DoS protection mechanisms."""
        # Check for rate limiting
        if 'rate_limit' in code.lower() or 'failed_attempts' in code:
            self.success('DoS Protection', f'{filename}: Rate limiting implemented')

        # Check for timeout on operations
        if re.search(r'timeout=|asyncio\.wait_for', code):
            self.success('DoS Protection', f'{filename}: Operation timeouts present')
        else:
            self.warning('DoS Protection',
                       f'{filename}: No operation timeouts detected', filename)

        # Check for connection limits
        if 'max_connections' in code:
            self.success('DoS Protection',
                       f'{filename}: Connection limits (DoS protection)')

        # Check for buffer size limits
        if re.search(r'limit=\d+|maxsize=\d+', code):
            self.success('DoS Protection', f'{filename}: Buffer size limits configured')

        # Check for slowloris protection (timeout)
        if 'idle' in code.lower() or 'inactivity' in code.lower():
            self.success('DoS Protection',
                       f'{filename}: Inactivity detection (slowloris protection)')

    def audit_server_module(self):
        """Audit all server module files."""
        print("=" * 70)
        print("PACKETQTH SERVER MODULE SECURITY AUDIT")
        print("=" * 70)
        print()

        server_dir = Path('server')
        if not server_dir.exists():
            print("ERROR: server/ directory not found")
            return

        # Audit server files
        for py_file in ['telnet.py', 'session.py']:
            file_path = server_dir / py_file
            if file_path.exists():
                self.audit_file(file_path)

    def generate_report(self):
        """Generate final report."""
        print("=" * 70)
        print("SERVER SECURITY AUDIT REPORT")
        print("=" * 70)
        print()

        # Summary
        critical = len([i for i in self.issues if i['severity'] == 'CRITICAL'])
        high = len([i for i in self.issues if i['severity'] == 'HIGH'])
        medium = len([i for i in self.issues if i['severity'] == 'MEDIUM'])
        warnings = len(self.warnings)
        passed = len(self.passed)

        print(f"Files Audited: {', '.join(self.files_audited)}")
        print()
        print(f"Summary:")
        print(f"  🔴 CRITICAL: {critical}")
        print(f"  🟠 HIGH:     {high}")
        print(f"  🟡 MEDIUM:   {medium}")
        print(f"  ⚠️  Warnings: {warnings}")
        print(f"  ✅ Passed:   {passed}")
        print()

        if critical > 0:
            print("🔴 CRITICAL ISSUES (Fix Immediately)")
            print("-" * 70)
            for issue in [i for i in self.issues if i['severity'] == 'CRITICAL']:
                print(f"  [{issue['category']}] {issue['file']}")
                print(f"    {issue['message']}")
                if issue['recommendation']:
                    print(f"    → {issue['recommendation']}")
            print()

        if high > 0:
            print("🟠 HIGH PRIORITY ISSUES")
            print("-" * 70)
            for issue in [i for i in self.issues if i['severity'] == 'HIGH']:
                print(f"  [{issue['category']}] {issue['file']}")
                print(f"    {issue['message']}")
                if issue['recommendation']:
                    print(f"    → {issue['recommendation']}")
            print()

        if medium > 0:
            print("🟡 MEDIUM PRIORITY ISSUES")
            print("-" * 70)
            for issue in [i for i in self.issues if i['severity'] == 'MEDIUM']:
                print(f"  [{issue['category']}] {issue['file']}")
                print(f"    {issue['message']}")
                if issue['recommendation']:
                    print(f"    → {issue['recommendation']}")
            print()

        if warnings > 0:
            print("⚠️  WARNINGS (Review Recommended)")
            print("-" * 70)
            for warning in self.warnings:
                print(f"  [{warning['category']}] {warning['file']}")
                print(f"    {warning['message']}")
            print()

        # Overall assessment
        print("=" * 70)
        print("OVERALL ASSESSMENT")
        print("=" * 70)

        if critical > 0:
            print("❌ FAIL - Critical security issues must be addressed")
            return 1
        elif high > 0:
            print("⚠️  CAUTION - High priority issues should be fixed")
            return 1
        elif medium > 0 or warnings > 0:
            print("✅ ACCEPTABLE - Minor issues noted")
            print("   Server module is reasonably secure")
            return 0
        else:
            print("✅ EXCELLENT - No significant security issues detected")
            return 0


# Run audit
audit = ServerSecurityAudit()
audit.audit_server_module()
exit_code = audit.generate_report()
sys.exit(exit_code)
