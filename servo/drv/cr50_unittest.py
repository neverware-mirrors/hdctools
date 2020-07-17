# Copyright (c) 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import mock
import re
import unittest

import cr50
import pty_driver

@mock.patch('servo.drv.pty_driver.ptyDriver._issue_cmd_get_results')
class TestPromptDetection(unittest.TestCase):
    class cr50(cr50.cr50):
        def __init__(self):
            pass
        _logger = mock.MagicMock()

    def test_normal_prompt(self, issueCmdMock):
        issueCmdMock.return_value = "value"
        uut = self.cr50()
        self.assertEquals('value', uut._issue_cmd_get_results('cmd\n', []))
        issueCmdMock.assert_called_with('cmd\n', [], flush=None,
                                        timeout=pty_driver.DEFAULT_UART_TIMEOUT)

    def test_spurious_prompt(self, issueCmdMock):
        def fakeIssueCmd(*args, **kwargs):
            if issueCmdMock.call_count >= cr50.cr50.PROMPT_DETECTION_TRIES:
                return 'value'
            else:
                raise pty_driver.ptyError('error')
        issueCmdMock.side_effect = fakeIssueCmd
        uut = self.cr50()
        self.assertEquals('value', uut._issue_cmd_get_results('cmd\n', []))
        issueCmdMock.assert_called_with('cmd\n', [], flush=None,
                                        timeout=pty_driver.DEFAULT_UART_TIMEOUT)
        # Prompt detection tries + issue of actual command
        self.assertEquals(cr50.cr50.PROMPT_DETECTION_TRIES+1,
                          issueCmdMock.call_count)

    def test_no_prompt(self, issueCmdMock):
        issueCmdMock.side_effect = pty_driver.ptyError('error')
        uut = self.cr50()
        with self.assertRaises(pty_driver.ptyError):
            uut._issue_cmd_get_results('cmd\n', [])
        self.assertEquals(cr50.cr50.PROMPT_DETECTION_TRIES,
                          issueCmdMock.call_count)
