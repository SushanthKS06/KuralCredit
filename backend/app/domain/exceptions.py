from __future__ import annotations


class DomainError(Exception):
    pass


class InvalidAmountError(DomainError):
    pass


class UnsupportedPeriodError(DomainError):
    pass


class IncompatibleComparisonError(DomainError):
    pass
