from localcosmos_server.analytics.models import AnonymousLog

class WithLogEntry:

    default_event_type = 'pageVisit'
    default_event_content = '/download'

    def create_log_entry(self, app, event_type=None, event_content=None, **kwargs):

        if event_type == None:
            event_type = self.default_event_type

        if event_content == None:
            event_content = self.default_event_content

        log_entry = AnonymousLog(
            app=app,
            event_type=event_type,
            event_content=event_content,
            **kwargs
        )

        log_entry.save()

        return log_entry