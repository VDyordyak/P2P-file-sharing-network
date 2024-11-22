SUCCESS = "(SUCCESSFUL)"
FAILURE = "(FAILED)"

class torrent_error(RuntimeError): 
    def __init__(self, error_msg): 
        self.error_msg = error_msg
    def __str__(self):
        return str(self.error_msg)
