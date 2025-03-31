# (c) 2023 Project Harmony.AI
import os
import requests
import json
import time
import logging

# Get values from environment variables
ENDPOINT_URL = os.environ.get("ENDPOINT_URL") or ""
HARMONY_API_KEY = os.environ.get("HARMONY_API_KEY") or ""

# Errors
ERROR_API_KEY_INVALID = 'error_api_key_invalid'
ERROR_API_KEY_RATE_LIMIT_EXHAUSTED = 'error_api_key_rate_limit_exhausted'

class ApiKeyServiceStats:
    def __init__(self, data: dict):
        self.api_key = data.get("apiKey")
        self.tier_name = data.get("tierName")
        self.service = data.get("service")
        self.requests_last_minute = data.get("requestsLastMinute")
        self.request_timestamps_delta = data.get("requestTimestampsDelta")
        self.requests_last_day = data.get("requestsLastDay")
        self.requests_per_minute_limit = data.get("requestsPerMinuteLimit")
        self.requests_per_day_limit = data.get("requestsPerDayLimit")
        self.cache_timeout = data.get("cacheTimeout")


class ApiKeyCacheManager:
    # _instance = None
    _api_key_cache = dict()

    # def __new__(cls):
    #     if cls._instance is None:
    #         cls._instance = super(ApiKeyCacheManager, cls).__new__(cls)
    #     return cls._instance

    @classmethod
    def _is_cache_valid(cls, api_key: str) -> bool:
        cached_entry = cls._api_key_cache.get(api_key)
        if not cached_entry:
            return False

        cached_stats, cache_timestamp = cached_entry
        current_time = time.time()
        if current_time - cache_timestamp > cached_stats.cache_timeout:
            # Cache has expired
            return False

        return True

    @classmethod
    def _register_cache_stats_event(cls, api_key: str):
        cached_entry = cls._api_key_cache.get(api_key)
        if not cached_entry:
            logging.log(logging.WARNING, f"Unable to add event for API Key '{api_key}'")
            return

        cached_stats, cache_timestamp = cached_entry
        current_timestamp = time.time()
        time_since_cached = cache_timestamp - current_timestamp
        cached_stats.request_timestamps_delta.append(time_since_cached)
        cached_stats.requests_last_day += 1

    @classmethod
    def _get_stats_for_api_key(cls, api_key: str, service: str) -> tuple:
        # Check cache validity first
        if cls._is_cache_valid(api_key):
            return cls._api_key_cache[api_key]

        # Build Request
        headers = {
            "Content-Type": "application/json",
            "Harmony-Api-Key": HARMONY_API_KEY
        }
        request_body = {
            "apiKey": api_key,
            "service": service
        }

        try:
            response = requests.post(f"{ENDPOINT_URL}/check", headers=headers, data=json.dumps(request_body), timeout=10)
            response.raise_for_status()

            stats = ApiKeyServiceStats(response.json())
            current_timestamp = time.time()

            stats_cache_data = (stats, current_timestamp)
            cls._api_key_cache[api_key] = stats_cache_data  # Cache the stats with timestamp

            return stats_cache_data
        except requests.ConnectionError:
            logging.log(logging.ERROR, "Failed to connect to the server. Please check your internet connection and try again.")
        except requests.Timeout:
            logging.log(logging.ERROR, "The request timed out. The server might be busy or down. Please try again later.")
        except requests.HTTPError:
            logging.log(logging.ERROR, f"HTTP error occurred: {response.status_code} - {response.text}")
        except json.JSONDecodeError:
            logging.log(logging.ERROR, "Failed to decode the server response. The server might have returned unexpected data.")
        except Exception as e:
            logging.log(logging.ERROR, f"An error occurred: {str(e)}")

        return None

    @classmethod
    def check_request_allowed_by_rate_limit(cls, api_key: str, service: str) -> (bool, str):
        if len(ENDPOINT_URL) == 0:
            return True, "apikey check disabled"

        if api_key is None or len(api_key) == 0:
            return False, ERROR_API_KEY_INVALID

        # Get cache data if possible
        stats_cache_data = cls._get_stats_for_api_key(api_key=api_key, service=service)
        if stats_cache_data is None:
            logging.log(logging.WARNING, f"Unable to obtain stats for API Key '{api_key}'")
            return False, ERROR_API_KEY_INVALID

        # Expand tuple
        stats, cached_time = stats_cache_data
        # determine time since cached
        current_timestamp = time.time()
        time_since_cached = cached_time - current_timestamp
        check_window = time_since_cached + 60
        # Count requests in the last minute
        requests_last_minute_count = sum(1 for delta in stats.request_timestamps_delta if delta <= check_window)
        # Evaluate Rate limit
        rate_limit_ok = requests_last_minute_count < stats.requests_per_minute_limit and stats.requests_last_day < stats.requests_per_day_limit
        if not rate_limit_ok:
            return False, ERROR_API_KEY_RATE_LIMIT_EXHAUSTED
        return True, ""

    @classmethod
    def register_rate_limiting_event(cls, api_key: str, service: str, event_type: str, user_ip: str):
        if len(ENDPOINT_URL) == 0:
            return

        # Get cache data if possible
        stats_cache_data = cls._get_stats_for_api_key(api_key=api_key, service=service)
        if stats_cache_data is None:
            logging.log(logging.WARNING, f"Unable to obtain stats for API Key '{api_key}'")
            return

        # Build Request
        headers = {
            "Content-Type": "application/json",
            "Harmony-Api-Key": HARMONY_API_KEY
        }
        request_body = {
            "apiKey": api_key,
            "service": service,
            "eventType": event_type,
            "ipAddress": user_ip
        }

        event_id = None
        try:
            response = requests.post(f"{ENDPOINT_URL}/event", headers=headers, data=json.dumps(request_body), timeout=10)
            response.raise_for_status()
            response_json = response.json()
            event_id = response_json["eventID"]
        except requests.ConnectionError:
            logging.log(logging.ERROR, "Failed to connect to the server. Please check your internet connection and try again.")
        except requests.Timeout:
            logging.log(logging.ERROR, "The request timed out. The server might be busy or down. Please try again later.")
        except requests.HTTPError:
            logging.log(logging.ERROR, f"HTTP error occurred: {response.status_code} - {response.text}")
        except json.JSONDecodeError:
            logging.log(logging.ERROR, "Failed to decode the server response. The server might have returned unexpected data.")
        except Exception as e:
            logging.log(logging.ERROR, f"An error occurred: {str(e)}")

        if event_id is None:
            logging.log(logging.WARNING, "Unable to keep track of events currently.")

        # store event in cache
        cls._register_cache_stats_event(api_key=api_key)


# # Example usage:
# if __name__ == "__main__":
#     request_dto = GetRateLimitAndStatsForAPIKeyRequest(api_key="YOUR_API_KEY", service="YOUR_SERVICE")
#     result = call_endpoint(request_dto)
#     print(result.api_key, result.tier_name, result.service)  # you can access other attributes as needed
