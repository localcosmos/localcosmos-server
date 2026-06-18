class BasePointsAwarder:
    
    def __init__(self, app):
        self.app = app
    
    def award_points(self, user, content_object):
        raise NotImplementedError("Subclasses must implement this method")