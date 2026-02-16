"""
PacketQTH Telnet Session Handler

Manages individual telnet connections with authentication and command processing.
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable, TYPE_CHECKING
from datetime import datetime, timedelta
from auth import TOTPAuthenticator, SessionManager, Session

if TYPE_CHECKING:
    from commands import CommandHandler

logger = logging.getLogger(__name__)


class TelnetSession:
    """
    Manages a single telnet connection.

    Features:
    - TOTP authentication
    - Inactivity timeout
    - Line-based text I/O
    - Command processing loop
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        authenticator: TOTPAuthenticator,
        session_manager: SessionManager,
        command_handler: Optional['CommandHandler'] = None,
        timeout_seconds: int = 300,
        max_auth_attempts: int = 3,
        bpq_mode: bool = True
    ):
        """
        Initialize telnet session.

        Args:
            reader: AsyncIO stream reader
            writer: AsyncIO stream writer
            authenticator: TOTP authenticator instance
            session_manager: Session manager instance
            command_handler: CommandHandler instance (optional)
            timeout_seconds: Inactivity timeout in seconds
            max_auth_attempts: Maximum authentication attempts
            bpq_mode: BPQ compatibility mode - expects callsign as first line (default: True)
        """
        self.reader = reader
        self.writer = writer
        self.authenticator = authenticator
        self.session_manager = session_manager
        self.command_handler = command_handler
        self.timeout_seconds = timeout_seconds
        self.max_auth_attempts = max_auth_attempts
        self.bpq_mode = bpq_mode

        # Session state
        self.authenticated = False
        self.callsign: Optional[str] = None
        self.session: Optional[Session] = None
        self.last_activity = datetime.now()

        # Connection info
        peername = writer.get_extra_info('peername')
        self.remote_addr = f"{peername[0]}:{peername[1]}" if peername else "unknown"

        logger.info(f"New connection from {self.remote_addr} (BPQ mode: {bpq_mode})")

    async def send(self, text: str, newline: bool = True):
        """
        Send text to client.

        Args:
            text: Text to send
            newline: Add CRLF line ending (default: True)
        """
        if newline:
            text += "\r\n"

        try:
            self.writer.write(text.encode('utf-8', errors='replace'))
            await self.writer.drain()
            self.last_activity = datetime.now()
        except Exception as e:
            logger.error(f"Error sending to {self.remote_addr}: {e}")
            raise

    async def send_lines(self, *lines: str):
        """
        Send multiple lines of text.

        Args:
            *lines: Lines to send
        """
        for line in lines:
            await self.send(line)

    async def read_line(self, prompt: str = "", timeout: Optional[int] = None) -> Optional[str]:
        """
        Read a line of input from client.

        Args:
            prompt: Optional prompt to display
            timeout: Read timeout in seconds (uses session timeout if None)

        Returns:
            Input line (stripped) or None on timeout/disconnect
        """
        if prompt:
            await self.send(prompt, newline=False)

        timeout_val = timeout or self.timeout_seconds

        try:
            # Read with timeout
            line_bytes = await asyncio.wait_for(
                self.reader.readline(),
                timeout=timeout_val
            )

            if not line_bytes:
                # Connection closed
                logger.info(f"Connection closed by {self.remote_addr}")
                return None

            # Decode and strip
            line = line_bytes.decode('utf-8', errors='replace').strip()

            self.last_activity = datetime.now()
            return line

        except asyncio.TimeoutError:
            logger.info(f"Timeout waiting for input from {self.remote_addr}")
            return None

        except Exception as e:
            logger.error(f"Error reading from {self.remote_addr}: {e}")
            return None

    async def authenticate(self) -> bool:
        """
        Perform TOTP authentication.

        In BPQ mode, expects callsign as first line (sent by BPQ automatically).
        In standard mode, prompts for callsign.

        Returns:
            True if authenticated, False otherwise
        """
        logger.info(f"Starting authentication for {self.remote_addr}")

        for attempt in range(1, self.max_auth_attempts + 1):
            # Get callsign
            if self.bpq_mode and attempt == 1:
                # BPQ mode: read callsign without prompting (BPQ sends it automatically)
                logger.debug(f"BPQ mode: waiting for callsign from {self.remote_addr}")
                callsign = await self.read_line("", timeout=60)
            else:
                # Standard mode: prompt for callsign
                callsign = await self.read_line("Callsign: ", timeout=60)

            if callsign is None:
                logger.info(f"Authentication aborted (no callsign) from {self.remote_addr}")
                return False

            callsign = callsign.upper().strip()

            if not callsign:
                if self.bpq_mode and attempt == 1:
                    # BPQ sent empty line - switch to standard mode and prompt
                    logger.debug(f"No callsign received in BPQ mode, switching to prompt mode")
                    self.bpq_mode = False
                    callsign = await self.read_line("Callsign: ", timeout=60)
                    if not callsign:
                        await self.send("Callsign required.")
                        continue
                    callsign = callsign.upper().strip()
                else:
                    await self.send("Callsign required.")
                    continue

            # Check if rate limited
            if self.authenticator.is_rate_limited(callsign):
                logger.warning(f"Rate limited authentication attempt for {callsign} from {self.remote_addr}")
                await self.send("Too many failed attempts. Try again in 5 minutes.")
                return False

            # Get TOTP code
            totp_code = await self.read_line("TOTP Code: ", timeout=60)

            if totp_code is None:
                logger.info(f"Authentication aborted (no TOTP) for {callsign} from {self.remote_addr}")
                return False

            totp_code = totp_code.strip()

            if not totp_code or len(totp_code) != 6 or not totp_code.isdigit():
                await self.send("Invalid code format (must be 6 digits).")
                continue

            # Verify TOTP
            success, message = self.authenticator.verify_totp(callsign, totp_code)

            if success:
                # Create session
                session_id = self.session_manager.create_session(callsign)
                self.session = self.session_manager.get_session(session_id)
                self.authenticated = True
                self.callsign = callsign

                logger.info(f"Successful authentication: {callsign} from {self.remote_addr}")
                await self.send("")
                await self.send(f"Welcome {callsign}!")
                await self.send("Type H for help")
                await self.send("")
                return True

            else:
                logger.warning(
                    f"Failed authentication attempt {attempt}/{self.max_auth_attempts} "
                    f"for {callsign} from {self.remote_addr}"
                )
                await self.send(message)

                if attempt < self.max_auth_attempts:
                    await self.send(f"Try again ({self.max_auth_attempts - attempt} attempts remaining).")
                    await self.send("")

        # Max attempts reached
        logger.warning(f"Max authentication attempts reached from {self.remote_addr}")
        await self.send("Maximum authentication attempts exceeded.")
        return False

    async def show_banner(self, banner: str):
        """
        Display welcome banner.

        Args:
            banner: Banner text (may contain multiple lines)
        """
        if banner:
            for line in banner.split('\n'):
                await self.send(line)
            await self.send("")

    async def command_loop(self):
        """
        Main command processing loop.

        Reads commands from user and processes them until quit or timeout.
        """
        if not self.authenticated:
            logger.error(f"Command loop called without authentication from {self.remote_addr}")
            return

        logger.info(f"Entering command loop for {self.callsign}")

        # Import here to avoid circular imports
        from commands import parse_command, validate_command, ValidationError, CommandType
        from formatting import format_error_message

        while True:
            # Check session validity
            if self.session and self.session.is_expired(self.timeout_seconds // 60):
                logger.info(f"Session expired for {self.callsign}")
                await self.send("Session expired due to inactivity.")
                break

            # Read command with prompt
            user_input = await self.read_line("> ")

            if user_input is None:
                # Timeout or disconnect
                logger.info(f"Command loop ended for {self.callsign} (timeout/disconnect)")
                break

            if not user_input:
                # Empty line, continue
                continue

            # Update session activity
            if self.session:
                self.session.update_activity()

            # Parse command
            command = parse_command(user_input)

            # Check if command parsed successfully
            if not command.is_valid():
                error_lines = format_error_message(command.error)
                for line in error_lines:
                    await self.send(line)
                continue

            # Handle quit command (special case - exit loop)
            if command.type == CommandType.QUIT:
                logger.info(f"User {self.callsign} quit")
                await self.send("73!")
                break

            # Check if this is a write operation requiring TOTP
            if command.is_write_operation():
                # Prompt for fresh TOTP code
                await self.send("")
                totp_code = await self.read_line("TOTP Code: ", timeout=60)

                if totp_code is None:
                    logger.info(f"Write operation aborted (timeout) for {self.callsign}")
                    await self.send("Operation cancelled.")
                    continue

                totp_code = totp_code.strip()

                # Validate TOTP format
                if not totp_code or len(totp_code) != 6 or not totp_code.isdigit():
                    await self.send("Invalid code format (must be 6 digits).")
                    await self.send("")
                    continue

                # Verify TOTP
                success, message = self.authenticator.verify_totp(self.callsign, totp_code)

                if not success:
                    logger.warning(f"Failed TOTP verification for write operation by {self.callsign}")
                    await self.send(message)
                    await self.send("")
                    continue

                # TOTP verified - proceed with write operation
                logger.info(f"TOTP verified for write operation by {self.callsign}")

            # Validate and execute command
            try:
                if self.command_handler:
                    # Validate command if handler has entity mapper
                    if hasattr(self.command_handler, 'mapper'):
                        validate_command(command, self.command_handler.mapper)

                    # Execute command
                    response_lines = await self.command_handler.handle(command)

                    # Send response
                    if response_lines:
                        for line in response_lines:
                            await self.send(line)
                else:
                    # No command handler - show error
                    await self.send("ERR: Command handler not initialized")
                    logger.error(f"No command handler available for {self.callsign}")

            except ValidationError as e:
                # Command validation failed
                error_lines = format_error_message(e.message, e.suggestion)
                for line in error_lines:
                    await self.send(line)

            except Exception as e:
                # Unexpected error
                logger.error(f"Error processing command '{user_input}' for {self.callsign}: {e}", exc_info=True)
                error_lines = format_error_message("Command processing error")
                for line in error_lines:
                    await self.send(line)

    async def run(self, banner: str = ""):
        """
        Run the complete session: banner, auth, command loop.

        Args:
            banner: Welcome banner to display

        Returns:
            None
        """
        try:
            # Show banner
            if banner:
                await self.show_banner(banner)

            # Authenticate
            if not await self.authenticate():
                await self.send("Authentication failed. Goodbye.")
                return

            # Enter command loop
            await self.command_loop()

        except Exception as e:
            logger.error(f"Session error for {self.remote_addr}: {e}")

        finally:
            # Cleanup
            await self.close()

    async def close(self):
        """Close the connection and cleanup session."""
        logger.info(f"Closing connection from {self.remote_addr} (user: {self.callsign or 'unauthenticated'})")

        # End session
        if self.session:
            self.session_manager.end_session(self.session.session_id)

        # Close writer
        try:
            if not self.writer.is_closing():
                self.writer.close()
                await self.writer.wait_closed()
        except Exception as e:
            logger.error(f"Error closing connection: {e}")

    def is_authenticated(self) -> bool:
        """Check if session is authenticated."""
        return self.authenticated

    def get_callsign(self) -> Optional[str]:
        """Get authenticated callsign."""
        return self.callsign

    def get_remote_addr(self) -> str:
        """Get remote address."""
        return self.remote_addr

    def get_idle_time(self) -> float:
        """
        Get idle time in seconds.

        Returns:
            Seconds since last activity
        """
        return (datetime.now() - self.last_activity).total_seconds()
