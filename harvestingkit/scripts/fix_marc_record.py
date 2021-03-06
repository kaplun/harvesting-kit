# -*- coding: utf-8 -*-
##
## This file is part of Harvesting Kit.
## Copyright (C) 2014 CERN.
##
## Harvesting Kit is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Harvesting Kit is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Harvesting Kit; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
from __future__ import print_function
import re
import sys
import getopt
from xml.dom.minidom import parse


def collapse_initials(name):
    """ Removes the space between initials.
        eg T. A. --> T.A."""
    if len(name.split()) > 1:
        name = re.sub(r'([A-Z]\.) +(?=[A-Z]\.)', r'\1', name)
    return name


def fix_name_capitalization(lastname, givennames):
    """ Converts capital letters to lower keeps first letter capital. """
    lastnames = lastname.split()
    if len(lastnames) == 1:
        if '-' in lastname:
            names = lastname.split('-')
            names = map(lambda a: a[0] + a[1:].lower(), names)
            lastname = '-'.join(names)
        else:
            lastname = lastname[0] + lastname[1:].lower()
    else:
        names = []
        for name in lastnames:
            if re.search(r'[A-Z]\.', name):
                names.append(name)
            else:
                names.append(name[0] + name[1:].lower())
        lastname = ' '.join(names)
        lastname = collapse_initials(lastname)
    names = []
    for name in givennames:
        if re.search(r'[A-Z]\.', name):
            names.append(name)
        else:
            names.append(name[0] + name[1:].lower())
    givennames = ' '.join(names)
    return lastname, givennames


def fix_title_capitalization(title):
    words = []
    for word in title.split():
        if word.upper() != word:
            words.append(word)
        else:
            words.append(word.lower())
    title = " ".join(words)
    title = title[0].upper() + title[1:]
    return title


def fix_authors(marcxml):
    datafields = marcxml.getElementsByTagName('datafield')
    # fix author names
    author_tags = []
    for tag in datafields:
        if tag.getAttribute('tag') in ['100', '700']:
            author_tags.append(tag)
    for tag in author_tags:
        for subfield in tag.getElementsByTagName('subfield'):
            if subfield.getAttribute('code') == 'a':
                author = ''
                for child in subfield.childNodes:
                    if child.nodeType == child.TEXT_NODE:
                        author += child.nodeValue
                if author:
                    author = author.replace(', Rapporteur', '')
                    if author.find(',') >= 0:
                        lastname, givennames = author.split(',')
                        lastname = lastname.strip()
                        givennames = givennames.strip()
                        initials = r'([A-Z]\.)'
                        if re.search(initials, lastname) and not \
                                re.search(initials, givennames):
                            lastname, givennames = givennames, lastname
                        lastname, givennames = fix_name_capitalization(
                            lastname, givennames.split()
                        )
                        givennames = collapse_initials(givennames)
                        subfield.firstChild.nodeValue = "%s, %s" %\
                            (lastname, givennames)
                    else:
                        names = author.split()
                        lastname, givennames = names[-1], names[:-1]
                        lastname, givennames = fix_name_capitalization(
                            lastname, givennames
                        )
                        givennames = collapse_initials(givennames)
                        subfield.firstChild.nodeValue = "%s, %s" %\
                            (lastname, givennames)
    return marcxml


def fix_title(marcxml):
    datafields = marcxml.getElementsByTagName('datafield')
    title_tags = []
    for tag in datafields:
        if tag.getAttribute('tag') in ['242', '245', '246', '247']:
            title_tags.append(tag)
    for tag in title_tags:
        for subfield in tag.getElementsByTagName('subfield'):
            if subfield.getAttribute('code') in ['a', 'b']:
                for child in subfield.childNodes:
                    if child.nodeType == child.TEXT_NODE:
                        title = child.nodeValue
                        title = fix_title_capitalization(title)
                        child.nodeValue = title
    return marcxml


def main():
    usage = """
    save to file:
    python fix_marc_record.py marc_file.xml >> result_file.xml

    print to terminal:
    python fix_marc_record.py marc_file.xml

    options:
    --recid -r
    fix the record with the given record id from https://inspireheptest.cern.ch
    e.g. python fix_marc_record.py --recid=1291107
    --site -s
    specify a different site useful only when option --recid or -r enabled
    e.g. python fix_marc_record.py -r 1291107 -s http://inspirehep.net
    """
    try:
        opts, args = getopt.getopt(sys.argv[1:], "r:s:", ["recid=", "site="])
        options = map(lambda a: a[0], opts)
        if len(args) > 1:
            raise getopt.GetoptError("Too many arguments given!!!")
        elif not args and not ('-r' in options or '--recid' in options):
            raise getopt.GetoptError("Missing argument record to fix")
    except getopt.GetoptError as err:
        print(str(err))  # will print something like "option -a not recognized"
        print(usage)
        sys.exit(2)

    if '-r' in options or '--recid' in options:
        from invenio.invenio_connector import InvenioConnector
        from xml.dom.minidom import parseString
        site = "http://inspireheptest.cern.ch/"
        for o, a in opts:
            if o in ['-s', '--site']:
                site = a
            if o in ['-r', '--recid']:
                recid = a
        inspiretest = InvenioConnector(site)
        record = inspiretest.search(p='001:%s' % recid, of='xm')
        marcxml = parseString(record)
        try:
            marcxml = marcxml.getElementsByTagName('record')[0]
        except IndexError:
            print("Record not found")
            sys.exit(2)

        marcxml = fix_authors(marcxml)
        marcxml = fix_title(marcxml)

        print(marcxml.toxml())
    else:
        filename = args[0]
        marcxml = parse(filename)

        marcxml = fix_authors(marcxml)
        marcxml = fix_title(marcxml)
        print(marcxml.toxml())


if __name__ == '__main__':
    main()
