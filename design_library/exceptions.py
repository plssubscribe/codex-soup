"""Custom exceptions for the 3D design library."""


class DesignLibraryError(Exception):
    """Base exception for all design library errors."""


class DesignNotFoundError(DesignLibraryError):
    """Raised when a design cannot be located."""


class DesignValidationError(DesignLibraryError):
    """Raised when design data fails validation."""
