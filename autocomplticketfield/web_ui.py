# encoding: utf-8

import json

from pkg_resources import resource_filename

from genshi.filters.transform import Transformer
from genshi.builder import tag

from trac.core import Component, implements
from trac.web.chrome import Chrome
from trac.util.compat import *
from trac.web.api import IRequestFilter, ITemplateStreamFilter, IRequestHandler
from trac.web.chrome import ITemplateProvider, add_script, add_stylesheet

from trac.ticket import TicketSystem
from trac.cache import cached


class TicketAutoCompleteTicketFieldPlugin (Component):

    ID = 'autocomplticketfield'
    SECTION = ID
    CLASS = ID
    CLASS_MULTI = ID + '-multi'

    implements(ITemplateProvider, IRequestFilter, ITemplateStreamFilter, IRequestHandler)

    @cached
    def fields (self):
        ts = TicketSystem(self.env)
        sect = self.env.config['ticket-custom']

        fields = {}

        for field in [f for f in ts.fields if f['type'] == 'text']:
            name = field['name']
            if field['type'] != 'text' or field.get('format', '') != 'list':
                continue
            options = sect.get(name + '.options')
            if options:
                fields[name] = {
                    'options': sorted([v.strip() for v in options.split('|')]),
                    'multiselect': sect.getbool(name + '.multiselect'),
                }

        return fields


    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        yield self.ID, resource_filename(__name__, 'htdocs')
    def get_templates_dirs(self):
        return []


    # IRequestFilter
    def pre_process_request (self, req, handler):
        return handler
    def post_process_request (self, req, template, data, content_type):
        if template in ('ticket.html', 'query.html'):
            Chrome(self.env).add_jquery_ui(req)
            add_script(req, self.ID + '/js/autocomplticketfield.js')
            if template == 'query.html':
                add_script(req, self.ID + '/js/jquery-observe.js')
        return template, data, content_type


    # ITemplateStreamFilter
    def filter_stream (self, req, method, filename, stream, data):
        if filename not in ('ticket.html', 'query.html'):
            return stream

        if filename == 'ticket.html':
            xpath = self._field_xpaths()
            if xpath:
                stream |= Transformer(xpath).attr('class', self.CLASS)
            xpath = self._field_xpaths(True)
            if xpath:
                stream |= Transformer(xpath).attr('class', self.CLASS_MULTI)

        if filename == 'query.html':
            xpath = self._field_xpaths_q()
            if xpath:
                stream |= Transformer(xpath).attr('class', self.CLASS)

        return stream


    def _field_names (self, multi=False):
        if multi:
            return [k for k,v in self.fields.items() if v['multiselect']]
        else:
            return [k for k,v in self.fields.items() if not v['multiselect']]

    def _field_xpaths (self, multi=False):
        field_names = self._field_names(multi)
        if field_names:
            conditions = ['@id="field-%s"' % n for n in field_names]
            return '//input[' + ' or '.join(conditions) + ']'
        return None

    def _field_xpaths_q (self):
        field_names = self._field_names() + self._field_names(True)
        if field_names:
            conditions = ['@class="%s"' % n for n in field_names]
            return '//fieldset[@id="filters"]//tr[' + ' or '.join(conditions) +\
                    ']/td[@class="filter"]/input'
        return None


    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith('/ticketfield_completion')

    def process_request(self, req):
        data = {
            'single': [n for n,f in self.fields.items() if not f['multiselect']],
            'multi':  [n for n,f in self.fields.items() if     f['multiselect']],
            'options': {}
        }
        for name,field in self.fields.items():
            data['options'][name] = field['options']
        req.send(json.dumps(data).encode('utf-8'), 'application/json')
