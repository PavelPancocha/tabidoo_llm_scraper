from __future__ import annotations

from .constants import ExitCode


class CliError(Exception):
    exit_code: ExitCode = ExitCode.SUCCESS


class InvalidConfigError(CliError):
    exit_code = ExitCode.INVALID_CONFIG


class AuthError(CliError):
    exit_code = ExitCode.AUTH


class NetworkError(CliError):
    exit_code = ExitCode.NETWORK


class ApiError(CliError):
    exit_code = ExitCode.API


class UserInputError(CliError):
    exit_code = ExitCode.USER_INPUT


class HttpStatusError(ApiError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
