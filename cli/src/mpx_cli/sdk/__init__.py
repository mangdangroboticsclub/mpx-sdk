"""mpx-cli SDK — cross-compatible robot communication, toolchain, and gateway utilities."""

from mpx_cli.sdk.connection import RobotClient, DEFAULT_HOST, DEFAULT_PORT
from mpx_cli.sdk.toolchain import (
    Toolchain,
    detect_all,
    compile_file,
    validate_wasm,
    inspect_wasm,
    CompileResult,
)
from mpx_cli.sdk.gateway import GatewayClient, GatewayError, DEFAULT_GATEWAY_URL
from mpx_cli.sdk.auth import (
    read_token,
    write_token,
    clear_token,
    get_username_from_token,
    read_state,
    write_state,
)

__all__ = [
    "RobotClient",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "GatewayClient",
    "GatewayError",
    "DEFAULT_GATEWAY_URL",
    "read_token",
    "write_token",
    "clear_token",
    "get_username_from_token",
    "read_state",
    "write_state",
    "Toolchain",
    "detect_all",
    "compile_file",
    "validate_wasm",
    "inspect_wasm",
    "CompileResult",
]
