"""External service integrations."""

from .smtp_email import (
    SMTPConfig,
    SMTPEmailService,
    EmailMessage,
    EmailAttachment,
    SendResult,
    get_smtp_service,
    configure_smtp_service,
)
from .scheduling import (
    SchedulingProvider,
    MeetingType,
    InjectionStyle,
    AvailabilitySlot,
    SchedulingLink,
    SchedulingConfig,
    SchedulingService,
    SchedulingConfigStorage,
    MessageInjector,
    CalendlyClient,
    CalComClient,
    validate_scheduling_url,
    create_scheduling_link,
    detect_provider,
    get_config_storage,
)

__all__ = [
    # SMTP Email
    "SMTPConfig",
    "SMTPEmailService",
    "EmailMessage",
    "EmailAttachment",
    "SendResult",
    "get_smtp_service",
    "configure_smtp_service",
    # Enums
    "SchedulingProvider",
    "MeetingType",
    "InjectionStyle",
    # Models
    "AvailabilitySlot",
    "SchedulingLink",
    "SchedulingConfig",
    # Services
    "SchedulingService",
    "SchedulingConfigStorage",
    "MessageInjector",
    # API Clients
    "CalendlyClient",
    "CalComClient",
    # Functions
    "validate_scheduling_url",
    "create_scheduling_link",
    "detect_provider",
    "get_config_storage",
]
