class AppPilotError(Exception):
    """Base AppPilot error."""


class ProviderUnavailable(AppPilotError):
    pass


class AuthorizationRequired(AppPilotError):
    pass


class PackageNotFound(AppPilotError):
    pass


class InstallationFailed(AppPilotError):
    pass


class RemovalFailed(AppPilotError):
    pass


class UpdateFailed(AppPilotError):
    pass


class InvalidPackage(AppPilotError, ValueError):
    pass


class ExecutableMissing(AppPilotError):
    pass


class OperationError(AppPilotError):
    pass
