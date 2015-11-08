#!/usr/bin/python

# Copyright (c) 2015 Ansible Project Contributors
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

from oslo_config.iniparser import BaseParser
from oslo_config.iniparser import ParseError  # noqa

DOCUMENTATION = '''
---
module: os_ini_reader
short_description: Read OpenStack INI format config files
version_added: "2.0"
author: "Ansible Project"
description:
  - Read INI-format configuration, with support for OpenStack's particular
    variant.
options:
  collision:
    description:
      - controls the behavior of the parser when encountering multiple
        keys with the same name.  If 'append', all option values will be
        lists and duplicate keys will create additional list entries.  If
        'replace', duplicate keys will replace the previous value (and
        entries will be scalar values rather than lists).
  path:
    description:
      - Path to an INI-format configuration file.
  section:
    description:
      - Limit returned information to a single section of the
        INI document.
'''

RETURN = '''
ini:
  description: >
    contents of the given ini file as a dictionary of
    dictionaries.
'''

EXAMPLES = '''
- name: read nova.conf into nova_conf variable
  os_ini_reader:
    path: /etc/nova/nova.conf
  register nova_conf

- name: access the sql_connection setting
  debug:
    var: nova_conf.ini.DEFAULT.sql_connection
'''

COLLISION_REPLACE = 1
COLLISION_APPEND = 2


class ConfigParser (BaseParser):
    def __init__(self,
                 collision=COLLISION_APPEND,
                 normalize_options=False,
                 normalize_sections=False,
                 option_xform=None,
                 section_xform=None,
                 literal_sections=None,
                 initial_section=None):

        super(ConfigParser, self).__init__()

        self.collision = collision
        self.normalize_options = normalize_options
        self.normalize_sections = normalize_sections
        self.option_xform = option_xform
        self.section_xform = section_xform
        self.literal_sections = literal_sections

        self.sections = {}
        self.section = initial_section

    def new_section(self, section):
        if (not self.literal_sections) or (
                section not in self.literal_sections):
            if self.normalize_sections:
                section = section.lower()
            if self.section_xform:
                section = self.section_xform(section)

        self.section = section
        self.sections.setdefault(self.section, {})

    def assignment(self, key, value):
        if not self.section:
            raise self.error_no_section(key)

        if self.normalize_options:
            key = key.lower()
        if self.option_xform:
            key = self.option_xform(key)

        value = '\n'.join(value)

        self.sections.setdefault(self.section, {})
        if self.collision == COLLISION_REPLACE:
            self.sections[self.section][key] = value
        else:
            self.sections[self.section].setdefault(key, [])
            self.sections[self.section][key].append(value)

    def error_no_section(self, key):
        return self.parse_exc('Section must be started before assignment',
                              self.lineno,
                              '%s = ...' % key)


def do_ini(module, path, section=None,
           collision=None):

    try:
        collision = {'replace': COLLISION_REPLACE,
                     'append': COLLISION_APPEND}[collision]
    except KeyError as exc:
        module.fail_json(msg='value of "collision" must be either "replace" '
                             'or "append".')

    cp = ConfigParser(collision=collision)

    with open(path) as f:
        try:
            cp.parse(f)
        except ParseError as exc:
            module.fail_json(msg='failed to parse %s: %s' % (
                path, exc))
        except IOError as exc:
            module.fail_json(msg='failed to read %s: %s' % (
                path, exc))

    if section:
        try:
            return cp.sections[section]
        except KeyError:
            module.fail_json(msg='%s has no section named "%s"' %
                             (section))
    else:
        return cp.sections


def main():

    module = AnsibleModule(
        argument_spec=dict(path=dict(required=True),
                           section=dict(),
                           collision=dict(default='append',
                                          choices=['append', 'replace'])),
        supports_check_mode=True)

    path = os.path.expanduser(module.params['path'])
    section = module.params['section']
    collision = module.params['collision']

    ini = do_ini(module, path, section, collision=collision)

    # Mission complete
    module.exit_json(path=path, changed=False, msg='OK', ini=ini)

# import module snippets
from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
