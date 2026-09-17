# -*- coding: utf-8 -*-
"""主动下载 wget：file_url 渲染前 shlex.quote，模板不再套一层引号。"""
import shlex

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.common.initiative_download_file import (
    render_initiative_download_script,
)


class InitiativeDownloadScriptQuoteTest(SimpleTestCase):
    def test_quotes_injectable_file_url(self):
        evil = 'https://bkrepo.example.com/generic/bk-dbm/medium/mysql/actuator/latest/x"; id; echo "'
        script = render_initiative_download_script(evil, "a" * 32, "bkrepo.example.com")
        self.assertIn('wget --header "Host:bkrepo.example.com" --tries=10  ' + shlex.quote(evil), script)
        self.assertNotIn('wget --header "Host:bkrepo.example.com" --tries=10  ' + evil, script)
        self.assertNotIn("; id", script.split(shlex.quote(evil))[0])

    def test_legal_url_stays_wget_argument(self):
        url = "https://bkrepo.example.com/generic/bk-dbm/medium/mysql/actuator/latest/dbactuator"
        script = render_initiative_download_script(url, "a" * 32, "bkrepo.example.com")
        self.assertIn('wget --header "Host:bkrepo.example.com" --tries=10  ' + shlex.quote(url), script)
        self.assertIn("-O dbactuator", script)
