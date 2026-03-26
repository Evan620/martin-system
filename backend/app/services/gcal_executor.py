"""
Shared single-threaded executor for all Google Calendar API calls.

httplib2 (used by the Google API client) is NOT thread-safe — concurrent
calls from different threads cause segfaults in the SSL layer.  Routing
every GCal call through one executor with max_workers=1 serialises them.
"""

import concurrent.futures

gcal_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="gcal-shared"
)
