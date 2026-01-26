"""Scheduling integration for Calendly, Cal.com, and custom scheduling links.

This module provides:
- Link validation for Calendly and Cal.com URLs
- Smart injection of scheduling links into outreach messages
- API client scaffolds for availability checking (when credentials provided)
- User scheduling preference configuration
"""

import logging
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class SchedulingProvider(str, Enum):
    """Supported scheduling service providers."""
    
    CALENDLY = "calendly"
    CALCOM = "calcom"
    CUSTOM = "custom"


class MeetingType(str, Enum):
    """Types of meetings for scheduling."""
    
    COFFEE_CHAT = "coffee_chat"
    INFORMATIONAL = "informational"
    INTERVIEW = "interview"
    NETWORKING = "networking"
    FOLLOW_UP = "follow_up"


class InjectionStyle(str, Enum):
    """How to inject the scheduling link into messages."""
    
    INLINE = "inline"          # Embedded naturally in text
    FOOTER = "footer"          # Added at the end of message
    CALL_TO_ACTION = "cta"     # As a clear call-to-action button/link


# URL validation patterns
CALENDLY_PATTERN = re.compile(
    r"^https?://(?:www\.)?calendly\.com/([a-zA-Z0-9_-]+)(?:/([a-zA-Z0-9_-]+))?/?$"
)

CALCOM_PATTERN = re.compile(
    r"^https?://(?:www\.)?(?:cal\.com|app\.cal\.com)/([a-zA-Z0-9_-]+)(?:/([a-zA-Z0-9_-]+))?/?$"
)


# =============================================================================
# Pydantic Models
# =============================================================================

class AvailabilitySlot(BaseModel):
    """An available time slot from the scheduling API."""
    
    start_time: datetime = Field(..., description="Start time of the available slot")
    end_time: datetime = Field(..., description="End time of the available slot")
    timezone: str = Field(default="UTC", description="Timezone of the slot")
    duration_minutes: int = Field(default=30, description="Duration of the meeting in minutes")
    is_available: bool = Field(default=True, description="Whether the slot is still available")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T10:30:00Z",
                "timezone": "America/New_York",
                "duration_minutes": 30,
                "is_available": True
            }
        }
    )
    
    @property
    def formatted_time(self) -> str:
        """Return a human-readable formatted time string."""
        return self.start_time.strftime("%A, %B %d at %I:%M %p")


class SchedulingLink(BaseModel):
    """A validated scheduling link with metadata."""
    
    url: str = Field(..., description="The full scheduling URL")
    provider: SchedulingProvider = Field(..., description="The scheduling provider")
    username: str = Field(..., description="Username/handle on the scheduling platform")
    event_type: str | None = Field(None, description="Specific event type slug if provided")
    display_name: str | None = Field(None, description="Human-friendly display name for the link")
    duration_minutes: int | None = Field(None, description="Expected meeting duration")
    is_valid: bool = Field(default=True, description="Whether the link has been validated")
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        """Ensure URL has https:// prefix."""
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        # Remove trailing slash for consistency
        return v.rstrip("/")
    
    @model_validator(mode="after")
    def validate_and_extract_info(self) -> "SchedulingLink":
        """Extract username and event type from URL based on provider."""
        if self.provider == SchedulingProvider.CALENDLY:
            match = CALENDLY_PATTERN.match(self.url)
            if match:
                self.username = match.group(1)
                self.event_type = match.group(2)
        elif self.provider == SchedulingProvider.CALCOM:
            match = CALCOM_PATTERN.match(self.url)
            if match:
                self.username = match.group(1)
                self.event_type = match.group(2)
        return self
    
    @property
    def short_url(self) -> str:
        """Return a shortened display version of the URL."""
        if self.provider == SchedulingProvider.CALENDLY:
            base = f"calendly.com/{self.username}"
        elif self.provider == SchedulingProvider.CALCOM:
            base = f"cal.com/{self.username}"
        else:
            return self.url
        
        if self.event_type:
            base += f"/{self.event_type}"
        return base


class SchedulingConfig(BaseModel):
    """User's scheduling preferences and configuration."""
    
    user_id: str = Field(..., description="User ID this config belongs to")
    primary_link: SchedulingLink | None = Field(None, description="Primary scheduling link")
    links: list[SchedulingLink] = Field(default_factory=list, description="All configured scheduling links")
    default_meeting_type: MeetingType = Field(
        default=MeetingType.COFFEE_CHAT,
        description="Default meeting type for scheduling"
    )
    default_duration_minutes: int = Field(
        default=30,
        ge=15,
        le=120,
        description="Default meeting duration in minutes"
    )
    injection_style: InjectionStyle = Field(
        default=InjectionStyle.INLINE,
        description="How to inject scheduling links into messages"
    )
    timezone: str = Field(default="America/New_York", description="User's preferred timezone")
    
    # API credentials (optional, for availability checking)
    calendly_api_key: str | None = Field(None, description="Calendly API key for availability checking")
    calcom_api_key: str | None = Field(None, description="Cal.com API key for availability checking")
    
    # Preferences for link injection
    include_availability_in_message: bool = Field(
        default=False,
        description="Whether to include specific availability times in messages"
    )
    availability_days_ahead: int = Field(
        default=7,
        ge=1,
        le=30,
        description="How many days ahead to check availability"
    )
    
    model_config = ConfigDict(from_attributes=True)
    
    def get_link_for_provider(self, provider: SchedulingProvider) -> SchedulingLink | None:
        """Get the first link for a specific provider."""
        for link in self.links:
            if link.provider == provider:
                return link
        return None
    
    def get_effective_link(self) -> SchedulingLink | None:
        """Get the primary link or first available link."""
        if self.primary_link:
            return self.primary_link
        if self.links:
            return self.links[0]
        return None


# =============================================================================
# Link Validation Functions
# =============================================================================

def detect_provider(url: str) -> SchedulingProvider | None:
    """Detect the scheduling provider from a URL.
    
    Args:
        url: The scheduling URL to analyze.
        
    Returns:
        The detected SchedulingProvider or None if not recognized.
    """
    url = url.lower().strip()
    
    if "calendly.com" in url:
        return SchedulingProvider.CALENDLY
    elif "cal.com" in url:
        return SchedulingProvider.CALCOM
    
    return None


def validate_scheduling_url(url: str) -> tuple[bool, SchedulingProvider | None, str | None]:
    """Validate a scheduling URL and detect its provider.
    
    Args:
        url: The URL to validate.
        
    Returns:
        Tuple of (is_valid, provider, error_message).
    """
    if not url:
        return False, None, "URL cannot be empty"
    
    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    provider = detect_provider(url)
    
    if provider is None:
        return False, None, "URL does not match Calendly or Cal.com patterns"
    
    if provider == SchedulingProvider.CALENDLY:
        if CALENDLY_PATTERN.match(url):
            return True, provider, None
        else:
            return False, provider, "Invalid Calendly URL format. Expected: calendly.com/username or calendly.com/username/event-type"
    
    elif provider == SchedulingProvider.CALCOM:
        if CALCOM_PATTERN.match(url):
            return True, provider, None
        else:
            return False, provider, "Invalid Cal.com URL format. Expected: cal.com/username or cal.com/username/event-type"
    
    return False, None, "Unknown provider"


def create_scheduling_link(url: str, display_name: str | None = None) -> SchedulingLink:
    """Create a validated SchedulingLink from a URL.
    
    Args:
        url: The scheduling URL.
        display_name: Optional human-friendly name for the link.
        
    Returns:
        A validated SchedulingLink object.
        
    Raises:
        ValueError: If the URL is not valid.
    """
    is_valid, provider, error = validate_scheduling_url(url)
    
    if not is_valid:
        raise ValueError(f"Invalid scheduling URL: {error}")
    
    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    # Extract username from URL
    username = ""
    event_type = None
    
    if provider == SchedulingProvider.CALENDLY:
        match = CALENDLY_PATTERN.match(url)
        if match:
            username = match.group(1)
            event_type = match.group(2)
    elif provider == SchedulingProvider.CALCOM:
        match = CALCOM_PATTERN.match(url)
        if match:
            username = match.group(1)
            event_type = match.group(2)
    
    return SchedulingLink(
        url=url,
        provider=provider,
        username=username,
        event_type=event_type,
        display_name=display_name,
        is_valid=True
    )


# =============================================================================
# Message Injection Functions
# =============================================================================

class MessageInjector:
    """Helper class for injecting scheduling links into outreach messages."""
    
    # Phrases that indicate a good place to inject a scheduling link
    SCHEDULING_TRIGGERS = [
        "let me know",
        "would you be available",
        "would love to chat",
        "happy to connect",
        "grab coffee",
        "set up a time",
        "schedule a call",
        "find a time",
        "meet for",
        "catch up",
    ]
    
    # Templates for different injection styles
    INLINE_TEMPLATES = {
        MeetingType.COFFEE_CHAT: "I'd love to grab coffee - feel free to book a time that works for you: {link}",
        MeetingType.INFORMATIONAL: "I'd appreciate the chance to learn more about your work. Here's my calendar: {link}",
        MeetingType.INTERVIEW: "Please feel free to book a time for us to connect: {link}",
        MeetingType.NETWORKING: "Would love to connect! You can book time here: {link}",
        MeetingType.FOLLOW_UP: "Let's continue our conversation - here's my calendar: {link}",
    }
    
    FOOTER_TEMPLATES = {
        MeetingType.COFFEE_CHAT: "\n\nBook a time for coffee: {link}",
        MeetingType.INFORMATIONAL: "\n\nSchedule an informational chat: {link}",
        MeetingType.INTERVIEW: "\n\nBook your interview slot: {link}",
        MeetingType.NETWORKING: "\n\nLet's connect: {link}",
        MeetingType.FOLLOW_UP: "\n\nContinue our conversation: {link}",
    }
    
    CTA_TEMPLATES = {
        MeetingType.COFFEE_CHAT: "\n\n[Schedule a Coffee Chat]({link})",
        MeetingType.INFORMATIONAL: "\n\n[Book an Informational Call]({link})",
        MeetingType.INTERVIEW: "\n\n[Schedule Interview]({link})",
        MeetingType.NETWORKING: "\n\n[Connect With Me]({link})",
        MeetingType.FOLLOW_UP: "\n\n[Book Follow-up Call]({link})",
    }
    
    @classmethod
    def inject_link(
        cls,
        message: str,
        link: SchedulingLink,
        style: InjectionStyle = InjectionStyle.INLINE,
        meeting_type: MeetingType = MeetingType.COFFEE_CHAT,
        availability_text: str | None = None
    ) -> str:
        """Inject a scheduling link into an outreach message.
        
        Args:
            message: The original message text.
            link: The scheduling link to inject.
            style: The injection style to use.
            meeting_type: The type of meeting being scheduled.
            availability_text: Optional text describing availability.
            
        Returns:
            The message with the scheduling link injected.
        """
        link_url = link.url
        
        if style == InjectionStyle.INLINE:
            return cls._inject_inline(message, link_url, meeting_type, availability_text)
        elif style == InjectionStyle.FOOTER:
            return cls._inject_footer(message, link_url, meeting_type, availability_text)
        elif style == InjectionStyle.CALL_TO_ACTION:
            return cls._inject_cta(message, link_url, meeting_type, availability_text)
        
        return message
    
    @classmethod
    def _inject_inline(
        cls,
        message: str,
        link: str,
        meeting_type: MeetingType,
        availability_text: str | None
    ) -> str:
        """Inject link naturally inline in the message."""
        # Check if message already contains a scheduling-related phrase
        message_lower = message.lower()
        
        for trigger in cls.SCHEDULING_TRIGGERS:
            if trigger in message_lower:
                # Find the position and inject after the sentence containing the trigger
                idx = message_lower.find(trigger)
                # Find the end of the sentence
                sentence_end = message.find(".", idx)
                if sentence_end == -1:
                    sentence_end = message.find("!", idx)
                if sentence_end == -1:
                    sentence_end = len(message)
                
                # Insert the link after the sentence
                link_text = f" Feel free to book a time: {link}"
                return message[:sentence_end + 1] + link_text + message[sentence_end + 1:]
        
        # If no trigger found, append the template
        template = cls.INLINE_TEMPLATES.get(meeting_type, cls.INLINE_TEMPLATES[MeetingType.COFFEE_CHAT])
        
        # Add availability text if provided
        if availability_text:
            template += f" {availability_text}"
        
        # Add the link text naturally at the end
        if message.rstrip().endswith((".", "!", "?")):
            return message.rstrip() + " " + template.format(link=link)
        else:
            return message.rstrip() + ". " + template.format(link=link)
    
    @classmethod
    def _inject_footer(
        cls,
        message: str,
        link: str,
        meeting_type: MeetingType,
        availability_text: str | None
    ) -> str:
        """Inject link as a footer at the end of the message."""
        template = cls.FOOTER_TEMPLATES.get(meeting_type, cls.FOOTER_TEMPLATES[MeetingType.COFFEE_CHAT])
        footer = template.format(link=link)
        
        if availability_text:
            footer += f"\n{availability_text}"
        
        return message.rstrip() + footer
    
    @classmethod
    def _inject_cta(
        cls,
        message: str,
        link: str,
        meeting_type: MeetingType,
        availability_text: str | None
    ) -> str:
        """Inject link as a call-to-action."""
        template = cls.CTA_TEMPLATES.get(meeting_type, cls.CTA_TEMPLATES[MeetingType.COFFEE_CHAT])
        cta = template.format(link=link)
        
        if availability_text:
            cta += f"\n\n_{availability_text}_"
        
        return message.rstrip() + cta
    
    @classmethod
    def format_availability_text(
        cls,
        slots: list[AvailabilitySlot],
        max_slots: int = 3
    ) -> str:
        """Format availability slots into readable text.
        
        Args:
            slots: List of available time slots.
            max_slots: Maximum number of slots to include.
            
        Returns:
            Formatted availability text.
        """
        if not slots:
            return ""
        
        available = [s for s in slots if s.is_available][:max_slots]
        
        if not available:
            return ""
        
        if len(available) == 1:
            return f"I'm available {available[0].formatted_time}."
        
        times = [s.formatted_time for s in available]
        if len(times) == 2:
            return f"I'm available {times[0]} or {times[1]}."
        
        return f"I'm available {', '.join(times[:-1])}, or {times[-1]}."


# =============================================================================
# API Client Scaffolds
# =============================================================================

class CalendlyClient:
    """Client for interacting with the Calendly API.
    
    Requires a Calendly API key for authenticated requests.
    API documentation: https://developer.calendly.com/api-docs
    """
    
    BASE_URL = "https://api.calendly.com"
    
    def __init__(self, api_key: str):
        """Initialize the Calendly client.
        
        Args:
            api_key: Calendly API key (personal access token).
        """
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_current_user(self) -> dict[str, Any]:
        """Get the current authenticated user.
        
        Returns:
            User information dict.
        """
        client = await self._get_client()
        response = await client.get("/users/me")
        response.raise_for_status()
        return response.json()
    
    async def get_event_types(self, user_uri: str | None = None) -> list[dict[str, Any]]:
        """Get available event types for scheduling.
        
        Args:
            user_uri: Optional user URI to filter event types.
            
        Returns:
            List of event type dicts.
        """
        client = await self._get_client()
        params = {}
        if user_uri:
            params["user"] = user_uri
        
        response = await client.get("/event_types", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("collection", [])
    
    async def get_available_times(
        self,
        event_type_uri: str,
        start_time: datetime,
        end_time: datetime
    ) -> list[AvailabilitySlot]:
        """Get available time slots for an event type.
        
        Args:
            event_type_uri: The event type URI.
            start_time: Start of the availability window.
            end_time: End of the availability window.
            
        Returns:
            List of AvailabilitySlot objects.
        """
        client = await self._get_client()
        
        params = {
            "event_type": event_type_uri,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        response = await client.get("/event_type_available_times", params=params)
        response.raise_for_status()
        data = response.json()
        
        slots = []
        for item in data.get("collection", []):
            start = datetime.fromisoformat(item["start_time"].replace("Z", "+00:00"))
            # Default to 30 min if duration not specified
            duration = 30
            end = start + timedelta(minutes=duration)
            
            slots.append(AvailabilitySlot(
                start_time=start,
                end_time=end,
                duration_minutes=duration,
                is_available=item.get("status") == "available"
            ))
        
        return slots


class CalComClient:
    """Client for interacting with the Cal.com API.
    
    Requires a Cal.com API key for authenticated requests.
    API documentation: https://cal.com/docs/api
    """
    
    BASE_URL = "https://api.cal.com/v1"
    
    def __init__(self, api_key: str):
        """Initialize the Cal.com client.
        
        Args:
            api_key: Cal.com API key.
        """
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                params={"apiKey": self.api_key},
                timeout=30.0
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_me(self) -> dict[str, Any]:
        """Get the current authenticated user.
        
        Returns:
            User information dict.
        """
        client = await self._get_client()
        response = await client.get("/me")
        response.raise_for_status()
        return response.json()
    
    async def get_event_types(self) -> list[dict[str, Any]]:
        """Get available event types.
        
        Returns:
            List of event type dicts.
        """
        client = await self._get_client()
        response = await client.get("/event-types")
        response.raise_for_status()
        data = response.json()
        return data.get("event_types", [])
    
    async def get_availability(
        self,
        event_type_id: int,
        start_time: datetime,
        end_time: datetime,
        timezone: str = "UTC"
    ) -> list[AvailabilitySlot]:
        """Get available time slots for an event type.
        
        Args:
            event_type_id: The event type ID.
            start_time: Start of the availability window.
            end_time: End of the availability window.
            timezone: Timezone for the availability query.
            
        Returns:
            List of AvailabilitySlot objects.
        """
        client = await self._get_client()
        
        params = {
            "eventTypeId": event_type_id,
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
            "timeZone": timezone
        }
        
        response = await client.get("/availability", params=params)
        response.raise_for_status()
        data = response.json()
        
        slots = []
        for day_slots in data.get("slots", {}).values():
            for slot in day_slots:
                start = datetime.fromisoformat(slot["time"].replace("Z", "+00:00"))
                # Default to 30 min
                duration = 30
                end = start + timedelta(minutes=duration)
                
                slots.append(AvailabilitySlot(
                    start_time=start,
                    end_time=end,
                    timezone=timezone,
                    duration_minutes=duration,
                    is_available=True
                ))
        
        return sorted(slots, key=lambda s: s.start_time)


# =============================================================================
# Main Service Class
# =============================================================================

class SchedulingService:
    """Main service for scheduling integration.
    
    Provides a unified interface for:
    - Managing scheduling links
    - Validating and formatting URLs
    - Injecting links into outreach messages
    - Checking availability (when API credentials provided)
    """
    
    def __init__(
        self,
        calendly_api_key: str | None = None,
        calcom_api_key: str | None = None
    ):
        """Initialize the scheduling service.
        
        Args:
            calendly_api_key: Optional Calendly API key.
            calcom_api_key: Optional Cal.com API key.
        """
        self.calendly_client: CalendlyClient | None = None
        self.calcom_client: CalComClient | None = None
        
        if calendly_api_key:
            self.calendly_client = CalendlyClient(calendly_api_key)
        if calcom_api_key:
            self.calcom_client = CalComClient(calcom_api_key)
    
    async def close(self) -> None:
        """Close all API clients."""
        if self.calendly_client:
            await self.calendly_client.close()
        if self.calcom_client:
            await self.calcom_client.close()
    
    def validate_link(self, url: str) -> tuple[bool, str | None]:
        """Validate a scheduling URL.
        
        Args:
            url: The URL to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        is_valid, _, error = validate_scheduling_url(url)
        return is_valid, error
    
    def create_link(self, url: str, display_name: str | None = None) -> SchedulingLink:
        """Create a validated scheduling link.
        
        Args:
            url: The scheduling URL.
            display_name: Optional display name.
            
        Returns:
            A SchedulingLink object.
            
        Raises:
            ValueError: If the URL is invalid.
        """
        return create_scheduling_link(url, display_name)
    
    def inject_into_message(
        self,
        message: str,
        config: SchedulingConfig,
        meeting_type: MeetingType | None = None,
        availability_slots: list[AvailabilitySlot] | None = None
    ) -> str:
        """Inject a scheduling link into an outreach message.
        
        Args:
            message: The original message.
            config: The user's scheduling configuration.
            meeting_type: Optional meeting type override.
            availability_slots: Optional availability slots to include.
            
        Returns:
            The message with the scheduling link injected.
        """
        link = config.get_effective_link()
        if not link:
            logger.warning("No scheduling link configured")
            return message
        
        mt = meeting_type or config.default_meeting_type
        
        availability_text = None
        if config.include_availability_in_message and availability_slots:
            availability_text = MessageInjector.format_availability_text(availability_slots)
        
        return MessageInjector.inject_link(
            message=message,
            link=link,
            style=config.injection_style,
            meeting_type=mt,
            availability_text=availability_text
        )
    
    async def get_availability(
        self,
        link: SchedulingLink,
        days_ahead: int = 7
    ) -> list[AvailabilitySlot]:
        """Get availability for a scheduling link.
        
        Requires the appropriate API client to be configured.
        
        Args:
            link: The scheduling link to check.
            days_ahead: Number of days ahead to check.
            
        Returns:
            List of available time slots.
            
        Raises:
            ValueError: If API client not configured for the provider.
        """
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(days=days_ahead)
        
        if link.provider == SchedulingProvider.CALENDLY:
            if not self.calendly_client:
                raise ValueError("Calendly API key not configured")
            
            # Get event types and find matching one
            try:
                user = await self.calendly_client.get_current_user()
                user_uri = user.get("resource", {}).get("uri")
                event_types = await self.calendly_client.get_event_types(user_uri)
                
                # Find event type matching the link
                event_type_uri = None
                for et in event_types:
                    if link.event_type and link.event_type in et.get("slug", ""):
                        event_type_uri = et.get("uri")
                        break
                
                if not event_type_uri and event_types:
                    event_type_uri = event_types[0].get("uri")
                
                if event_type_uri:
                    return await self.calendly_client.get_available_times(
                        event_type_uri, start_time, end_time
                    )
            except Exception as e:
                logger.error(f"Error fetching Calendly availability: {e}")
                raise
        
        elif link.provider == SchedulingProvider.CALCOM:
            if not self.calcom_client:
                raise ValueError("Cal.com API key not configured")
            
            try:
                event_types = await self.calcom_client.get_event_types()
                
                # Find matching event type
                event_type_id = None
                for et in event_types:
                    if link.event_type and link.event_type in et.get("slug", ""):
                        event_type_id = et.get("id")
                        break
                
                if not event_type_id and event_types:
                    event_type_id = event_types[0].get("id")
                
                if event_type_id:
                    return await self.calcom_client.get_availability(
                        event_type_id, start_time, end_time
                    )
            except Exception as e:
                logger.error(f"Error fetching Cal.com availability: {e}")
                raise
        
        return []


# =============================================================================
# Configuration Storage
# =============================================================================

class SchedulingConfigStorage:
    """In-memory storage for scheduling configurations.
    
    In production, this would be backed by a database.
    """
    
    def __init__(self):
        """Initialize the storage."""
        self._configs: dict[str, SchedulingConfig] = {}
    
    def get(self, user_id: str) -> SchedulingConfig | None:
        """Get a user's scheduling configuration.
        
        Args:
            user_id: The user ID.
            
        Returns:
            The user's configuration or None if not found.
        """
        return self._configs.get(user_id)
    
    def save(self, config: SchedulingConfig) -> None:
        """Save a user's scheduling configuration.
        
        Args:
            config: The configuration to save.
        """
        self._configs[config.user_id] = config
    
    def delete(self, user_id: str) -> bool:
        """Delete a user's scheduling configuration.
        
        Args:
            user_id: The user ID.
            
        Returns:
            True if deleted, False if not found.
        """
        if user_id in self._configs:
            del self._configs[user_id]
            return True
        return False
    
    def update_link(
        self,
        user_id: str,
        url: str,
        display_name: str | None = None,
        set_as_primary: bool = False
    ) -> SchedulingConfig:
        """Add or update a scheduling link for a user.
        
        Args:
            user_id: The user ID.
            url: The scheduling URL.
            display_name: Optional display name.
            set_as_primary: Whether to set as primary link.
            
        Returns:
            The updated configuration.
        """
        config = self.get(user_id)
        if not config:
            config = SchedulingConfig(user_id=user_id)
        
        link = create_scheduling_link(url, display_name)
        
        # Check if link already exists
        existing_idx = None
        for i, existing in enumerate(config.links):
            if existing.url == link.url:
                existing_idx = i
                break
        
        if existing_idx is not None:
            config.links[existing_idx] = link
        else:
            config.links.append(link)
        
        if set_as_primary:
            config.primary_link = link
        
        self.save(config)
        return config


# Global storage instance (would be replaced with database in production)
_config_storage = SchedulingConfigStorage()


def get_config_storage() -> SchedulingConfigStorage:
    """Get the global configuration storage instance."""
    return _config_storage
