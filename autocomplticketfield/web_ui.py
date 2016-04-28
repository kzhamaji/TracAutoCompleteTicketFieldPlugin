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

try:
    from customdbtable.api import CustomDBTableSystem
    has_CustomDBTableSystem = True
except ImportError:
    has_CustomDBTableSystem = False


class TicketAutoCompleteTicketFieldPlugin (Component):

    ID = 'autocomplticketfield'
    SECTION = ID
    CLASS = ID
    CLASS_MULTI = ID + '-multi'

    implements(ITemplateProvider, IRequestFilter, ITemplateStreamFilter, IRequestHandler)

    def _get_fields (self):
        ts = TicketSystem(self.env)
        sect = self.env.config['ticket-custom']

        fields = {}

        for field in [f for f in ts.fields if f['type'] == 'text']:
            name = field['name']
            if field['type'] != 'text' or field.get('format', '') != 'list':
                continue

            options = None

            options_from = sect.get(name + '.options_from')
            if options_from:
                if options_from.startswith('customdb:') and has_CustomDBTableSystem:
                    elts = options_from.split(':', 1)[-1].split('/')
                    if elts[0]:
                        env, table, col = self.env, elts[0], elts[1]
                    else:
                        env = self._resolve_env(elts[1])
                        table, col = elts[2], elts[3]
                    options = CustomDBTableSystem(env).sorted_column(table, col)

            if not options:
                options = sect.get(name + '.options')
                options = sorted([v.strip() for v in options.split('|')])

            if options:
                fields[name] = {
                    'options': options,
                    'multiselect': sect.getbool(name + '.multiselect'),
                }

        return fields

    @property
    def fields (self):
        if not hasattr(self, "_fields"):
            self._fields = self._get_fields()
        return self._fields
 

    def _get_intertracs (self):
        # FIXME this assumes trac envs are arranged under the same directory
        intertracs = {}
        aliases = {}
        for key, value in self.env.config['intertrac'].options():
            if key.endswith('.url'):
                intertracs[key.split('.')[0]] = os.path.basename(value)
            else:
                aliases[key] = value
        for alias, to in aliases.items():
            if to in intertracs:
                intertracs[alias] = intertracs[to]
        return intertracs

    @property
    def _intertracs (self):
        if not hasattr(self, "__intertracs"):
            self.__intertracs = self._get_intertracs()
        return self.__intertracs

    def _resolve_env (self, name):
        from trac.env import open_environment
        import os.path
        dir_ = self._intertracs[name]
        path = os.path.join(os.path.dirname(self.env.path), dir_)
        return open_environment(path, True)


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
