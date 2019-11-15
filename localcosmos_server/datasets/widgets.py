from django.conf import settings
from django.contrib.gis import forms
from django.forms.widgets import *
from django.forms.utils import flatatt
from django.template import loader, Context
from django.utils.encoding import (
    force_str, force_text
)
from localcosmos_server.utils import datetime_from_cron

from django.utils.html import conditional_escape, format_html, html_safe


from localcosmos_server.taxonomy.widgets import TaxonAutocompleteWidget as BackboneTaxonAutocompleteWidget

import json

'''
    JSONWidget consist of one hidden TextInput (the json)
    and a verbose TextInput for interacting and displaying human-readable data
'''
class JSONWidget(forms.MultiWidget):

    def __init__(self, attrs=None):

        widgets = (
            forms.TextInput,
            forms.HiddenInput,
        )

        super().__init__(widgets, attrs=attrs)

    def verbose_value(self, value):
        raise NotImplementedError("JSONWidgets need to implement verbose_value")

    def value_to_json(self, value):
        raise NotImplementedError("JSONWidgets need to implement value_to_json")

    # value is eg datetime with timezone
    def decompress(self, value):
        """
        Return a list of decompressed values for the given compressed value.
        The given value can be assumed to be valid, but not necessarily
        non-empty.
        """

        if value:
            return [self.verbose_value(value), self.value_to_json(value)]
		
        return [None, None]


    def format_value(self, value):
        """
        Return a value as it should appear when rendered in a template.
        """
        if value:
            return [value[0], json.dumps(value[1])]
        
        return None
    

class MobileNumberInput(forms.NumberInput):

    template_name = 'datasets/widgets/mobile_number_input.html'


# data is geojson
class MobilePositionInput(JSONWidget):

    template_name = 'datasets/widgets/mobile_position_input.html'

    def value_to_json(self, value):
        if type(value) == str:
            return json.loads(value)
        return value

    def verbose_value(self, value):
        coords = value['geometry']['coordinates']
        verbose_position = '{0} {1} ({2}m)'.format(coords[0], coords[1], value['properties']['accuracy'])
        return verbose_position


    def get_context(self, name, value, attrs):

        if value and value != [None, None]:

            if isinstance(value, list):
                value = [value[0], self.value_to_json(value[1])]
            else:
                value = self.decompress(value)

        context = super().get_context(name, value, attrs)

        return context

        


from django.forms.widgets import Widget, Select
import re
import datetime, time
from django.utils.dates import MONTHS
from django.utils import datetime_safe
from django.utils.formats import get_format
from django.utils.safestring import mark_safe
from django.utils import timezone
class SelectDateTimeWidget(JSONWidget):
    """
    A Widget that splits date and time input into three <select> boxes.

    This also serves as an example of a Widget that has more than one HTML
    element and hence implements value_from_datadict.
    """

    template_name = 'datasets/widgets/select_datetime_widget.html'

    month_field = '%s_month'
    day_field = '%s_day'
    year_field = '%s_year'
    hour_field = '%s_hour'
    minute_field = '%s_minute'
    select_widget = Select

    date_re = re.compile(r'(\d{4})-(\d\d?)-(\d\d?):(\d\d?)-(\d\d?)$')


    def __init__(self, attrs=None, years=None, months=None, hours=None, minutes=None, empty_label=None):
        
        self.attrs = attrs or {}

        # Optional list or tuple of years to use in the "year" select box.
        if years:
            self.years = years
        else:
            this_year = datetime.date.today().year
            self.years = range(this_year -10, this_year+1)

        # Optional dict of months to use in the "month" select box.
        if months:
            self.months = months
        else:
            self.months = range(1,13)
            # self.months = MONTHS

        if hours:
            self.hours = hours
        else:
            self.hours = range(0, 24)

        if minutes:
            self.minutes = minutes
        else:
            self.minutes = range(0, 60)

        super().__init__(attrs)
        

    def value_to_json(self, datetime_obj):

        offset = datetime_obj.utcoffset()
        offset_minutes = int(-offset.seconds/60)

        temporal_json = {
            'type': 'Temporal',
            'cron': {
                    'type': 'timestamp',
                    'format' : 'unixtime',
                    'timestamp': int(datetime_obj.timestamp() * 1000),
                    'timezone_offset' : offset_minutes,
            },
        }

        return temporal_json
        

    def get_default_value(self):
        now = timezone.now()
        value_json = self.value_to_json(now)
        return [self.verbose_value(now), value_json]


    @staticmethod
    def _parse_date_fmt():
        fmt = get_format('DATETIME_FORMAT')
        escaped = False
        for char in fmt:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char in 'Yy':
                yield 'year'
            elif char in 'bEFMmNn':
                yield 'month'
            elif char in 'dj':
                yield 'day'
            elif char in 'P':
                yield 'hour'
                yield 'minute'

    # value is a list [verbose, json]
    def get_context(self, name, value, attrs):

        if not value or value == [None, None]:
            value = self.get_default_value()

        elif not isinstance(value, list):
            value = self.decompress(value)

        if (type(value[1]) == str):
            value = [value[0], json.loads(value[1])]

        dt = datetime_from_cron(value[1])
            
        try:
            year_val, month_val, day_val, hour_val, minute_val = dt.year, dt.month, dt.day, dt.hour, dt.minute
        except AttributeError:
            year_val = month_val = day_val = hour_val = minute_val = None
            if isinstance(value, str):
                if settings.USE_L10N:
                    try:
                        input_format = get_format('DATE_INPUT_FORMATS')[0]
                        v = datetime.datetime.strptime(force_str(value), input_format)
                        year_val, month_val, day_val, hour_val, minute_val = v.year, v.month, v.day, v.hour, v.minute
                    except ValueError:
                        pass
                if year_val is None:
                    match = self.date_re.match(value)
                    if match:
                        year_val, month_val, day_val, hour_val, minute_val = [int(val) for val in match.groups()]

        
        context = super().get_context(name, value, attrs)

        context['splitwidgets'] = {}
        
        choices = [(i, i) for i in self.years]
        context['splitwidgets']['year'] = self.create_select('year', name, self.year_field, year_val, choices)
    
        choices = [(i, i) for i in self.months]
        context['splitwidgets']['month'] = self.create_select('month', name, self.month_field, month_val, choices)

        choices = [(i, i) for i in range(1, 32)]
        context['splitwidgets']['day'] = self.create_select('day', name, self.day_field, day_val, choices)

        choices = [(i, i) for i in self.hours]
        context['splitwidgets']['hour'] = self.create_select('hours', name, self.hour_field, hour_val, choices)

        choices = [(i, i) for i in self.minutes]
        context['splitwidgets']['minute'] = self.create_select('minutes', name, self.minute_field, minute_val, choices)

        context['unixtime'] = int(time.mktime(dt.timetuple()) * 1000)
        context['mode'] = self.attrs.get('datetime_mode', 'datetime')


        #context['value'] = value

        return context
    

    def id_for_label(self, id_):
        for first_select in self._parse_date_fmt():
            return '%s_%s' % (id_, first_select)
        else:
            return '%s_month' % id_

    def create_select(self, datepart, name, field, val, choices):
        if 'id' in self.attrs:
            id_ = self.attrs['id']
        else:
            id_ = 'id_%s' % name

        attrs = {
            'id' : field % id_,
        }

        attrs['data-datepart'] = datepart
        local_attrs = self.build_attrs(attrs) #id=field % id_)
        s = self.select_widget(choices=choices)
        select_html = s.render(field % name, val, local_attrs)
        return select_html

    # value is a datetime object
    def verbose_value(self, value):
        if value:
            return value
        return ''


class CameraAndAlbumWidget(forms.FileInput):
    template_name = 'datasets/widgets/picture_widget.html'
    
