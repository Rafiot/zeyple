#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from mock import Mock
import email
import os
import shutil
from textwrap import dedent
from zeyple import zeyple

LINUS_ID = '79BE3E4300411886'

def is_encrypted(string):
    return string.startswith(b'-----BEGIN PGP MESSAGE-----')

class ZeypleTest(unittest.TestCase):
    def setUp(self):
        shutil.copyfile('tests/zeyple.conf', 'zeyple.conf')
        os.system("gpg --recv-keys %s 2> /dev/null" % LINUS_ID)
        self.zeyple = zeyple.Zeyple()
        self.zeyple._send_message = Mock() # don't try to send emails

    def tearDown(self):
        os.remove('zeyple.conf')

    def test__config(self):
        """Parses the configuration file properly"""

        self.assertEqual(
            self.zeyple._config.get('zeyple', 'log_file'),
           '/tmp/zeyple.log'
        )

    def test__user_key(self):
        """Returns the right ID for the given email address"""

        self.assertIsNone(self.zeyple._user_key('non_existant@example.org'))

        self.assertEqual(
            self.zeyple._user_key('torvalds@linux-foundation.org'),
            LINUS_ID
        )

    def test__encrypt_with_plain_text(self):
        """Encrypts plain text"""

        encrypted = self.zeyple._encrypt(
            'The key is under the carpet.', [LINUS_ID]
        )
        self.assertTrue(is_encrypted(encrypted))

    def test__encrypt_with_unicode(self):
        """Encrypts Unicode text"""

        encrypted = self.zeyple._encrypt('héhé', [LINUS_ID])
        self.assertTrue(is_encrypted(encrypted))

    def test_process_message_with_simple_message(self):
        """Encrypts simple messages"""

        emails = self.zeyple.process_message(dedent("""\
            Received: by example.org (Postfix, from userid 0)
                id DD3B67981178; Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            To: torvalds@linux-foundation.org
            Subject: Hello
            Message-Id: <20120906233537.DD3B67981178@example.org>
            Date: Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            From: root@example.org (root)

            test
        """), ["torvalds@linux-foundation.org"])

        self.assertIsNotNone(emails[0]['X-Zeyple'])
        self.assertTrue(is_encrypted(emails[0].get_payload()))


    def test_process_message_with_multipart_message(self):
        """Ignores multipart messages"""

        emails = self.zeyple.process_message(dedent("""\
            Return-Path: <torvalds@linux-foundation.org>
            Received: by example.org (Postfix, from userid 0)
                id CE9876C78258; Sat,  8 Sep 2012 13:00:18 +0000 (UTC)
            Date: Sat, 08 Sep 2012 13:00:18 +0000
            To: torvalds@linux-foundation.org
            Subject: test
            User-Agent: Heirloom mailx 12.4 7/29/08
            MIME-Version: 1.0
            Content-Type: multipart/mixed;
             boundary="=_504b4162.Gyt30puFsMOHWjpCATT1XRbWoYI1iR/sT4UX78zEEMJbxu+h"
            Message-Id: <20120908130018.CE9876C78258@example.org>
            From: root@example.org (root)

            This is a multi-part message in MIME format.

            --=_504b4162.Gyt30puFsMOHWjpCATT1XRbWoYI1iR/sT4UX78zEEMJbxu+h
            Content-Type: text/plain; charset=us-ascii
            Content-Transfer-Encoding: 7bit
            Content-Disposition: inline

            test

            --=_504b4162.Gyt30puFsMOHWjpCATT1XRbWoYI1iR/sT4UX78zEEMJbxu+h
            Content-Type: application/x-sh
            Content-Transfer-Encoding: base64
            Content-Disposition: attachment;
             filename="trac.sh"

            c3UgLWMgJ3RyYWNkIC0taG9zdG5hbWUgMTI3LjAuMC4xIC0tcG9ydCA4MDAwIC92YXIvdHJh
            Yy90ZXN0JyB3d3ctZGF0YQo=

            --=_504b4162.Gyt30puFsMOHWjpCATT1XRbWoYI1iR/sT4UX78zEEMJbxu+h--
        """), ["torvalds@linux-foundation.org"])

        self.assertIsNotNone(emails[0]['X-Zeyple'])
        self.assertTrue(emails[0].is_multipart())
        for part in emails[0].walk():
            self.assertFalse(is_encrypted(part.as_string().encode('utf-8')))

