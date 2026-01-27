from plugins.base_plugin.base_plugin import BasePlugin
from plugins.seniorDashboard_allDay.constants import LOCALE_MAP, FONT_SIZES, WEATHER_ICONS
from PIL import ImageColor
import icalendar
import recurring_ical_events
import logging
import requests
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

class SeniorDashboardAllDay(BasePlugin):
    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['style_settings'] = True
        template_params['locale_map'] = LOCALE_MAP
        return template_params

    def generate_image(self, settings, device_config):
        calendar_urls = settings.get('calendarURLs[]')
        calendar_colors = settings.get('calendarColors[]')
        view = "listMonth"  # Fixed to list view

        if not calendar_urls:
            raise RuntimeError("At least one calendar URL is required")
        for url in calendar_urls:
            if not url.strip():
                raise RuntimeError("Invalid calendar URL")

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]
        
        timezone = device_config.get_config("timezone", default="America/New_York")
        time_format = device_config.get_config("time_format", default="12h")
        tz = pytz.timezone(timezone)

        current_dt = datetime.now(tz)
        start, end = self.get_view_range(current_dt)
        logger.debug(f"Fetching events for {start} --> [{current_dt}] --> {end}")
        events = self.fetch_ics_events(calendar_urls, calendar_colors, tz, start, end)
        if not events:
            logger.warn("No events found for ics url")

        # Hardcode display options to True
        display_settings = settings.copy()
        display_settings["displayTitle"] = "true"
        display_settings["displayWeekends"] = "true"
        display_settings["displayEventTime"] = "true"
        
        # Ensure language is set (default to 'en' if not provided)
        if "language" not in display_settings or not display_settings["language"]:
            display_settings["language"] = "en"
        
        # Get locale for date formatting
        locale_code = display_settings.get("language", "en")
        
        # Fetch weather data
        weather_data = self.fetch_weather_data(timezone)
        
        template_params = {
            "view": view,
            "events": events,
            "current_dt": current_dt.replace(minute=0, second=0, microsecond=0).isoformat(),
            "timezone": timezone,
            "plugin_settings": display_settings,
            "time_format": time_format,
            "font_scale": FONT_SIZES.get(settings.get("fontSize", "normal")),
            "locale_code": locale_code,
            "weather": weather_data
        }

        image = self.render_image(dimensions, "seniorDashboard_allDay.html", "seniorDashboard_allDay.css", template_params)

        if not image:
            raise RuntimeError("Failed to take screenshot, please check logs.")
        return image
    
    def fetch_ics_events(self, calendar_urls, colors, tz, start_range, end_range):
        parsed_events = []

        for calendar_url, color in zip(calendar_urls, colors):
            cal = self.fetch_calendar(calendar_url)
            events = recurring_ical_events.of(cal).between(start_range, end_range)
            contrast_color = self.get_contrast_color(color)

            for event in events:
                start, end, all_day = self.parse_data_points(event, tz)
                parsed_event = {
                    "title": str(event.get("summary")),
                    "start": start,
                    "backgroundColor": color,
                    "textColor": contrast_color,
                    "allDay": all_day
                }
                if end:
                    parsed_event['end'] = end

                parsed_events.append(parsed_event)

        return parsed_events
    
    def get_view_range(self, current_dt):
        """Get the date range for listMonth view (5 weeks from today)."""
        start = datetime(current_dt.year, current_dt.month, current_dt.day)
        end = start + timedelta(weeks=5)
        return start, end
        
    def parse_data_points(self, event, tz):
        all_day = False
        dtstart = event.decoded("dtstart")
        if isinstance(dtstart, datetime):
            start = dtstart.astimezone(tz).isoformat()
        else:
            start = dtstart.isoformat()
            all_day = True

        end = None
        if "dtend" in event:
            dtend = event.decoded("dtend")
            if isinstance(dtend, datetime):
                end = dtend.astimezone(tz).isoformat()
            else:
                end = dtend.isoformat()
        elif "duration" in event:
            duration = event.decoded("duration")
            end = (dtstart + duration).isoformat()
        return start, end, all_day

    def fetch_calendar(self, calendar_url):
        # workaround for webcal urls
        if calendar_url.startswith("webcal://"):
            calendar_url = calendar_url.replace("webcal://", "https://")
        try:
            response = requests.get(calendar_url, timeout=30)
            response.raise_for_status()
            return icalendar.Calendar.from_ical(response.text)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch iCalendar url: {str(e)}")

    def get_contrast_color(self, color):
        """
        Returns '#000000' (black) or '#ffffff' (white) depending on the contrast
        against the given color.
        """
        r, g, b = ImageColor.getrgb(color)
        # YIQ formula to estimate brightness
        yiq = (r * 299 + g * 587 + b * 114) / 1000

        return '#000000' if yiq >= 150 else '#ffffff'

    def get_weather_icon(self, code):
        """Get weather icon emoji for a given weather code."""
        return WEATHER_ICONS.get(code, "❓")

    def fetch_weather_data(self, timezone):
        """Fetch weather data from Open-Meteo API."""
        URL = "https://api.open-meteo.com/v1/dwd-icon"
        
        # Default coordinates (can be made configurable later)
        params = {
            "latitude": 49.8728,
            "longitude": 8.6512,
            "current_weather": True,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "forecast_days": 3,
            "timezone": timezone
        }
        
        try:
            response = requests.get(URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process current weather
            current = data.get("current_weather", {})
            current_weather = {
                "icon": self.get_weather_icon(current.get("weathercode", 0)),
                "temperature": current.get("temperature", 0),
                "windspeed": current.get("windspeed", 0),
                "weathercode": current.get("weathercode", 0)
            }
            
            # Process daily forecast
            daily = data.get("daily", {})
            forecast = []
            if "time" in daily:
                for i, day in enumerate(daily["time"]):
                    # Format date in German format (DD.MM.YYYY)
                    try:
                        date_obj = datetime.strptime(day, "%Y-%m-%d")
                        formatted_date = date_obj.strftime("%d.%m.%Y")
                    except:
                        formatted_date = day  # Fallback to original if parsing fails
                    
                    forecast.append({
                        "date": formatted_date,
                        "icon": self.get_weather_icon(daily.get("weathercode", [0])[i] if i < len(daily.get("weathercode", [])) else 0),
                        "temp_min": daily.get("temperature_2m_min", [0])[i] if i < len(daily.get("temperature_2m_min", [])) else 0,
                        "temp_max": daily.get("temperature_2m_max", [0])[i] if i < len(daily.get("temperature_2m_max", [])) else 0,
                        "precipitation": daily.get("precipitation_sum", [0])[i] if i < len(daily.get("precipitation_sum", [])) else 0,
                        "weathercode": daily.get("weathercode", [0])[i] if i < len(daily.get("weathercode", [])) else 0
                    })
            
            return {
                "current": current_weather,
                "forecast": forecast
            }
        except Exception as e:
            logger.warning(f"Failed to fetch weather data: {str(e)}")
            return {
                "current": None,
                "forecast": []
            }
