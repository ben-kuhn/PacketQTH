"""
PacketQTH Telnet Interface Fuzzer

Corpus-based fuzzer (deterministic, seeded RNG) that verifies:

  1. The command parser never raises — always returns a Command object.
  2. The session command loop never crashes on any network input.
  3. The TOTP authenticator never raises on any callsign / token input.

All RNG uses a fixed seed so failures are reproducible; re-running the
suite with the same build always exercises the same inputs.
"""

import asyncio
import random
import string
import pytest
import pyotp
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from auth.totp import TOTPAuthenticator, SessionManager, Session
from commands.parser import parse_command
from commands.models import CommandType
from server.session import TelnetSession


# ---------------------------------------------------------------------------
# Corpus construction
# ---------------------------------------------------------------------------

SEED = 0xDEADBEEF


def _rng() -> random.Random:
    return random.Random(SEED)


def _rand_str(rng: random.Random, lo: int, hi: int,
               chars: str = string.printable) -> str:
    return ''.join(rng.choice(chars) for _ in range(rng.randint(lo, hi)))


# Hand-crafted inputs targeting specific code paths
HANDCRAFTED: list[str] = [
    # Empty / whitespace
    "", " ", "\t", "   ", "\r", "\n", "\r\n",

    # ASCII control characters
    "\x00", "\x01", "\x02",
    "\x03",           # ETX / Ctrl+C  — session should disconnect
    "\x04",           # EOT / Ctrl+D  — session should disconnect
    "\x1b",           # ESC
    "\x7f",           # DEL
    "\x08",           # BS

    # Telnet protocol bytes
    "\xff",                  # IAC
    "\xff\xf4",              # IAC IP (Interrupt Process)
    "\xff\xfb\x01",          # IAC WILL ECHO
    "\xff\xfd\x18",          # IAC DO TERM-TYPE
    "\xff\xf4\xff\xfd\x06",  # IAC IP IAC DO TIMING-MARK (common Ctrl+C)

    # Null bytes embedded in commands
    "ON\x001", "L\x002", "\x00ON 1", "ON 1\x00",

    # Very long inputs
    "A" * 1_000,
    "L " + "9" * 1_000,
    "ON " + "1" * 1_000,
    " " * 1_000,
    "X" * 10_000,

    # All valid commands with standard args
    "L", "L 1", "L 2", "L 99",
    "S 1", "S 99999",
    "ON 1", "ON 99999",
    "OFF 1", "OFF 99999",
    "SET 1 50", "SET 1 0", "SET 1 255",
    "A", "A 1",
    "T 1",
    "H", "R", "Q",
    "N", "P",

    # Wrong argument types
    "ON abc", "ON 1.5", "ON -1", "ON 0", "ON",
    "OFF abc", "OFF -999", "OFF",
    "SET 1", "SET abc 50", "SET 1 abc", "SET -1 50", "SET",
    "S -1", "S 0", "S abc", "S",
    "T -1", "T 0", "T abc", "T",
    "L -1", "L 0", "L abc",
    "A -1", "A abc",

    # Extra / missing tokens
    "L 1 2 3", "ON 1 2 3", "SET 1 50 extra", "H extra", "Q extra",

    # Whitespace variants
    "  L  ", "\tL\t", "L\t2", "ON\t1", "\t\tON\t\t1\t\t",

    # Mixed case
    "l", "on 1", "Off 1", "sEt 1 50", "QUIT", "quit", "hElP",

    # Numeric extremes
    f"ON {2**31}", f"ON {2**63}", f"ON {-2**31}",
    f"L {2**31}", f"L {2**63}",
    "SET 1 9.9e999", "SET 1 nan", "SET 1 inf", "SET 1 -inf",
    "SET 1 99999999999999", "SET 1 -99999999999999",

    # Unicode
    "L 台灣", "ON 🔥", "Ñoño 1",
    "\u0000\u0001\u0002",
    "\uffff", "\u200b", "\u202e",   # zero-width, RTL override

    # Injection attempts (must all be harmless)
    "L; ON 1", "L && ON 1", "L | ON 1",
    "L `ON 1`", "L $(ON 1)",
    "%s%s%s%s", "%d%d%d%d", "%n%n%n%n",
    "../../../etc/passwd",

    # Multiple commands crammed onto one line
    "L L L", "ON ON ON", "H H H",

    # Commands with embedded line endings (arrive as one readline call)
    "L\rON 1", "H\nON 1",
]


def _random_corpus(count: int = 300) -> list[str]:
    """Generate a deterministic random corpus."""
    rng = _rng()
    valid = ["L", "ON 1", "OFF 1", "S 1", "SET 1 50", "A", "H", "R", "T 1"]
    out: list[str] = []

    for _ in range(count):
        strategy = rng.randrange(5)
        if strategy == 0:
            out.append(_rand_str(rng, 0, 100))
        elif strategy == 1:
            raw = bytes(rng.randint(0, 255) for _ in range(rng.randint(1, 50)))
            out.append(raw.decode("utf-8", errors="replace"))
        elif strategy == 2:
            chars = list(rng.choice(valid))
            for _ in range(rng.randint(1, 5)):
                chars[rng.randrange(len(chars))] = chr(rng.randint(0, 127))
            out.append("".join(chars))
        elif strategy == 3:
            n = rng.randint(500, 5_000)
            out.append(_rand_str(rng, n, n))
        else:
            out.append("".join(chr(rng.randint(0, 31)) for _ in range(rng.randint(1, 20))))

    return out


FULL_CORPUS: list[str] = HANDCRAFTED + _random_corpus(300)


# ---------------------------------------------------------------------------
# Parser fuzzing
# ---------------------------------------------------------------------------

class TestParserFuzzing:
    """
    The parser must NEVER raise an exception regardless of input.
    It must always return a Command object (possibly with error set).
    """

    def test_never_raises(self):
        """parse_command() must not raise for any input in the corpus."""
        failures = []
        for i, inp in enumerate(FULL_CORPUS):
            try:
                result = parse_command(inp)
                assert result.type is not None, f"returned Command with None type"
            except Exception as e:
                failures.append((i, repr(inp[:60]), type(e).__name__, str(e)[:80]))

        if failures:
            detail = "\n".join(
                f"  [{i}] {s}: {etype}: {emsg}"
                for i, s, etype, emsg in failures[:10]
            )
            pytest.fail(f"{len(failures)} inputs raised in parser:\n{detail}")

    def test_unknown_always_has_error(self):
        """Every UNKNOWN command must carry a non-empty error string."""
        failures = []
        for inp in FULL_CORPUS:
            result = parse_command(inp)
            if result.type == CommandType.UNKNOWN and not result.error:
                failures.append(repr(inp[:60]))
        if failures:
            pytest.fail(
                f"{len(failures)} UNKNOWN results had no error:\n"
                + "\n".join(f"  {s}" for s in failures[:10])
            )

    def test_valid_commands_parse_correctly(self):
        """Well-formed commands must parse to the correct type with no error."""
        cases = [
            ("L",         CommandType.LIST),
            ("L 2",       CommandType.LIST),
            ("S 1",       CommandType.SHOW),
            ("ON 1",      CommandType.ON),
            ("OFF 1",     CommandType.OFF),
            ("SET 1 50",  CommandType.SET),
            ("A",         CommandType.AUTOMATIONS),
            ("A 3",       CommandType.AUTOMATIONS),
            ("T 1",       CommandType.TRIGGER),
            ("H",         CommandType.HELP),
            ("Q",         CommandType.QUIT),
            ("R",         CommandType.REFRESH),
        ]
        for raw, expected_type in cases:
            result = parse_command(raw)
            assert result.type == expected_type, \
                f"{raw!r}: expected {expected_type}, got {result.type}"
            assert result.error is None, \
                f"{raw!r}: unexpected error: {result.error!r}"


# ---------------------------------------------------------------------------
# Auth fuzzing
# ---------------------------------------------------------------------------

class TestAuthFuzzing:
    """
    verify_totp must never raise — always return (bool, str) — regardless
    of what is passed as callsign or token.
    """

    @pytest.fixture
    def auth(self, users_yaml):
        path, _ = users_yaml
        return TOTPAuthenticator(path)

    def test_verify_never_raises(self, auth):
        fuzz_callsigns = [
            "", " ", "A", "KN4XYZ", "kn4xyz",
            "A" * 1_000, "\x00", "\xff\xff", "123456",
            "../etc/passwd", "%s%s%s", "🔥", "\uffff",
        ] + _random_corpus(30)

        fuzz_tokens = [
            "", " ", "000000", "999999", "12345", "1234567",
            "abcdef", "      ", "123 456", "%s%s%s%s%s%s",
            "\x00" * 6, "\xff" * 6,
            "A" * 1_000,
        ] + _random_corpus(20)

        failures = []
        # Cross-product but keep it tractable: each callsign vs first 10 tokens
        for callsign in fuzz_callsigns:
            for token in fuzz_tokens[:10]:
                try:
                    result = auth.verify_totp(callsign, token)
                    assert isinstance(result, tuple) and len(result) == 2, \
                        "verify_totp did not return a 2-tuple"
                    assert isinstance(result[0], bool), "result[0] not bool"
                    assert isinstance(result[1], str),  "result[1] not str"
                except Exception as e:
                    failures.append(
                        (repr(callsign[:30]), repr(token[:20]), type(e).__name__)
                    )

        if failures:
            detail = "\n".join(
                f"  callsign={c} token={t}: {e}"
                for c, t, e in failures[:10]
            )
            pytest.fail(f"{len(failures)} verify_totp calls raised:\n{detail}")

    def test_replay_returns_false_not_raises(self, auth):
        """Presenting the same valid token twice must return False, not raise."""
        secret = list(auth.users.values())[0]
        callsign = list(auth.users.keys())[0]
        token = pyotp.TOTP(secret).now()

        r1 = auth.verify_totp(callsign, token)
        r2 = auth.verify_totp(callsign, token)

        assert r1 == (True, "Authentication successful."), \
            f"First use should succeed, got {r1}"
        assert r2[0] is False, \
            "Second use of same token should be rejected"


# ---------------------------------------------------------------------------
# Session command-loop fuzzing
# ---------------------------------------------------------------------------

class _SimpleHandler:
    """No-op command handler. No 'mapper' attribute so validation is skipped."""

    async def handle(self, command):
        return []


def _fuzz_session(inputs: list[str]) -> TelnetSession:
    """
    Build a TelnetSession already in authenticated state.

    The mock reader plays back `inputs` one line per readline() call then
    returns EOF. A no-op command handler is attached.
    """
    secret = pyotp.random_base32()

    auth = TOTPAuthenticator.__new__(TOTPAuthenticator)
    auth.users_file = "dummy.yaml"
    auth.users = {"FUZZ": secret}
    auth.failed_attempts = {}
    auth.used_tokens = {}

    sm = SessionManager()

    line_iter = iter(inputs)

    reader = AsyncMock(spec=asyncio.StreamReader)

    async def fake_readline():
        try:
            return (next(line_iter) + "\n").encode("utf-8", errors="replace")
        except StopIteration:
            return b""

    reader.readline = fake_readline

    writer = MagicMock(spec=asyncio.StreamWriter)
    writer.is_closing.return_value = False
    writer.get_extra_info.return_value = ("127.0.0.1", 9999)
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()

    session = TelnetSession(
        reader=reader,
        writer=writer,
        authenticator=auth,
        session_manager=sm,
        command_handler=_SimpleHandler(),
        timeout_seconds=300,
        bpq_mode=False,
    )

    # Skip the authentication flow — go straight to command loop
    session.authenticated = True
    session.callsign = "FUZZ"
    session.session = Session(
        callsign="FUZZ",
        authenticated_at=datetime.now(),
        last_activity=datetime.now(),
        session_id="fuzz-0000",
    )

    return session


class TestSessionFuzzing:
    """
    The command loop must survive any byte sequence from the network.
    The invariant: command_loop() must return normally (not raise) for
    every input, no matter how malformed.

    Input sequence per fuzz case:
      [fuzz_input, "000000", "Q", "Q"]

    "000000" absorbs the TOTP prompt that appears for write operations
    (it will be rejected as an invalid code and the loop continues).
    "Q" then cleanly exits the loop.
    """

    @pytest.mark.asyncio
    async def test_command_loop_never_crashes(self):
        """Full corpus: session loop must not raise on any input."""
        # Use HANDCRAFTED + 100-item random sample to keep runtime reasonable
        rng = _rng()
        random_inputs = _random_corpus(300)
        corpus = HANDCRAFTED + rng.sample(random_inputs, k=100)

        failures = []
        for i, fuzz in enumerate(corpus):
            session = _fuzz_session([fuzz, "000000", "Q", "Q"])
            try:
                await session.command_loop()
            except Exception as e:
                failures.append(
                    (i, repr(fuzz[:60]), type(e).__name__, str(e)[:80])
                )

        if failures:
            detail = "\n".join(
                f"  [{i}] {s}: {etype}: {emsg}"
                for i, s, etype, emsg in failures[:10]
            )
            pytest.fail(
                f"{len(failures)} inputs crashed the session loop:\n{detail}"
            )

    @pytest.mark.asyncio
    async def test_ctrl_c_ends_session_cleanly(self):
        """\\x03 / \\x04 must disconnect the session without raising."""
        for ctrl in ("\x03", "\x04", "\x03\x03", "\x04\x03", "H\x03"):
            session = _fuzz_session([ctrl, "Q"])
            await session.command_loop()   # must not raise

    @pytest.mark.asyncio
    async def test_ten_kb_input_handled(self):
        """A 10 kB single 'line' must not crash the session."""
        session = _fuzz_session(["X" * 10_000, "Q"])
        await session.command_loop()

    @pytest.mark.asyncio
    async def test_high_byte_and_null_input(self):
        """Binary-ish inputs must not crash the session."""
        nasty = [
            "\x00" * 100,
            "\xff" * 100,
            "\x00ON\x001\x00",
            "".join(chr(i % 256) for i in range(512)),
        ]
        for inp in nasty:
            session = _fuzz_session([inp, "Q"])
            await session.command_loop()

    @pytest.mark.asyncio
    async def test_rapid_fire_valid_commands(self):
        """Many valid commands in sequence must not cause state corruption."""
        cmds = (["L", "A", "H", "R", "N", "P", "S 1", "L 2"] * 50) + ["Q"]
        session = _fuzz_session(cmds)
        await session.command_loop()

    @pytest.mark.asyncio
    async def test_empty_lines_dont_hang(self):
        """Repeated empty input must not block indefinitely."""
        session = _fuzz_session([""] * 50 + ["Q"])
        await session.command_loop()
