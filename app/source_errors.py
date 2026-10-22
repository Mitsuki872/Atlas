"""User-facing source failures, distinct from corrupted data or application defects."""
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime

class SourceError(RuntimeError):
    def __init__(self,message,*,status=None,retryable=False,retry_after=0,attempts=1):
        super().__init__(message)
        self.status=status;self.retryable=retryable;self.retry_after=retry_after;self.attempts=attempts

def retry_after_seconds(value,now=None):
    if not value:return 0
    try:return max(0,int(value))
    except (ValueError,TypeError):pass
    try:
        target=parsedate_to_datetime(value)
        if target.tzinfo is None:target=target.replace(tzinfo=timezone.utc)
        return max(0,int((target-(now or datetime.now(timezone.utc))).total_seconds())+1)
    except (ValueError,TypeError,OverflowError):return 0
