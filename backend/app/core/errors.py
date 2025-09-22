class StreamingCompletionError(Exception):
    """
    Custom exception for streaming requests that finish without a STOP signal.
    """
    pass
