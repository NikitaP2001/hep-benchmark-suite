#!/usr/bin/env python3
###############################################################################
# Copyright 2019-2020 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################

from datetime import datetime
import json
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock
from hepbenchmarksuite.plugins import send_queue


class TestAMQ(unittest.TestCase):
    """AMQ send_queue functionality.

    Reads a minimal test json format2.0 from data/
    """

    # get CI environment args.
    # currently unused
    # TODO(anyone): fix for testing without gitlab CI vars
    ci_args = {
        "username": os.getenv("QUEUE_USERNAME"),
        "password": os.getenv("QUEUE_PASSWORD"),
        "server": os.getenv("QUEUE_HOST"),
        "port": os.getenv("QUEUE_PORT"),
        "topic": os.getenv("QUEUE_NAME"),
        "cert": os.getenv("CERT_FILE"),
        "key": os.getenv("KEY_FILE"),
    }

    def genJSON(self, message="None"):
        """Generate JSON with passed message, return its path."""
        # Currently unused
        self.assertTrue(isinstance(message, str), "Message is not a string")
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        self.test_json["_timestamp"] = self.test_json["_timestamp_end"] = timestamp
        self.test_json["host"]["freetext"] = message
        with open(self.test_file_path, "w") as profile:
            profile.write(json.dumps(self.test_json))
        return self.test_json

    def setUp(self):
        """Collect CI env and setup testing objects."""
        # currently unused

        self.test_dir = os.path.join(os.getcwd(), "tests/")
        self.test_file_path = os.path.join(self.test_dir, "/data/result_profile.json")

        # TODO(anyone): add better test json2.0 with other results
        with open(self.test_dir + "data/result_profile_db12.json", "r") as t:
            self.test_json = json.loads(t.read())
        self.assertTrue(isinstance(self.test_json, dict))

    @patch("builtins.open", new_callable=mock_open())
    def test_genJSON(self, mock_open_file):
        """Test if the json creation is successfull."""
        # currently unused
        ret = self.genJSON("testString")

        mock_open_file.assert_called_once_with(self.test_file_path, "w")
        mock_open_file.return_value.__enter__().write.assert_called_once_with(
            json.dumps(self.test_json)
        )
        self.assertDictEqual(ret, self.test_json)
        self.assertEqual(ret["host"]["freetext"], "testString")

    def test_parse_args(self):
        """Command-line arguments test."""
        parser = send_queue.parse_args(
            [
                "-p",
                "1",
                "-s",
                "google.com",
                "-u",
                "mickey",
                "-w",
                "mouse",
                "-t",
                "hepscore",
                "-k",
                "d",
                "-c",
                "cert:SSA!~!@",
                "-f",
                "howto.json",
            ]
        )
        self.assertEqual(parser.port, 1)
        self.assertEqual(parser.server, "google.com")
        self.assertEqual(parser.username, "mickey")
        self.assertEqual(parser.password, "mouse")
        self.assertEqual(parser.topic, "hepscore")
        self.assertEqual(parser.key, "d")
        self.assertEqual(parser.cert, "cert:SSA!~!@")
        self.assertEqual(parser.file, "howto.json")

        parser = send_queue.parse_args(["-s", "www", "-t", "topic", "-f", "foobar"])
        self.assertEqual(parser.port, 61613)
        self.assertEqual(parser.server, "www")
        self.assertEqual(parser.username, None)
        self.assertEqual(parser.password, None)
        self.assertEqual(parser.topic, "topic")
        self.assertEqual(parser.key, None)
        self.assertEqual(parser.cert, None)
        self.assertEqual(parser.file, "foobar")

        with self.assertRaises(SystemExit) as cm:
            parser = send_queue.parse_args([])
            self.assertEqual(cm.exception.code, 2)

        with self.assertRaises(SystemExit) as cm:
            parser = send_queue.parse_args(["-s"])
            self.assertEqual(cm.exception.code, 2)

        with self.assertRaises(SystemExit) as cm:
            parser = send_queue.parse_args(
                ["-s", "www", "-t", "topic", "-f", "foobar", "--port", "fifteen"]
            )
            self.assertEqual(cm.exception.code, 2)

    @patch("hepbenchmarksuite.plugins.send_queue.send_message")
    def test_main(self, mock_send_message):
        """Pass command line arguments to send_queue."""
        mock_result = send_queue.argparse.Namespace(
            cert=None,
            file="test.json",
            key=None,
            password=None,
            port=111,
            server="google.com",
            topic="a",
            username=None,
        )

        with patch.object(
            send_queue, "parse_args", return_value=mock_result
        ) as mock_parse_args:
            send_queue.main()
        mock_send_message.assert_called_once_with(
            "test.json", {"port": 111, "server": "google.com", "topic": "a"}
        )
        self.assertTrue(mock_parse_args.called)

    def test_file_path(self):

        with self.assertRaises(FileNotFoundError):
            send_queue.send_message("", dict())

        with patch(
            "hepbenchmarksuite.plugins.send_queue.Path.is_file", autospec=True
        ) as mock_filecheck:
            with self.assertRaises(FileNotFoundError):
                send_queue.send_message("garbage.json", dict())
        self.assertTrue(mock_filecheck.called)

    @patch("hepbenchmarksuite.plugins.send_queue.time.sleep", return_value=None)
    @patch("hepbenchmarksuite.plugins.send_queue.Listener", autospec=True)
    @patch("hepbenchmarksuite.plugins.send_queue.Path.is_file", return_value=True)
    @patch("hepbenchmarksuite.plugins.send_queue.stomp", autospec=True)
    def test_send_message(self, mock_stomp, mock_filecheck, mock_listener, mock_sleep):
        """Pass config object to send_queue"""
        test_args = {"port": 8181, "server": "home.cern", "topic": "test"}
        mock_conn = MagicMock()
        mock_stomp.Connection.return_value = mock_conn

        with self.assertRaises(FileNotFoundError):
            # test bad file read
            send_queue.send_message("garbage/file.json", dict())
            self.assertTrue(mock_filecheck.called)

        with patch.object(
            send_queue, "open", mock_open(read_data="{'test':1}")
        ) as mock_json:
            # mock the file read, and continue testing

            # Test no credentials
            with self.assertRaises(OSError):
                send_queue.send_message(self.test_file_path, test_args)
            mock_json.assert_called_once_with(self.test_file_path, "r")
            mock_stomp.Connection.assert_called_once_with(
                host_and_ports=[(test_args["server"], int(test_args["port"]))]
            )
            mock_conn.set_listener.assert_called_once_with(
                "mylistener", mock_listener(mock_conn)
            )
            mock_json.reset_mock()
            mock_stomp.reset_mock()
            mock_conn.reset_mock()

            # Test user/pw
            test_args = {
                "port": 8181,
                "server": "home.cern",
                "topic": "test",
                "username": "Dave",
                "password": "password",
            }
            with self.assertLogs(
                "hepbenchmarksuite.plugins.send_queue", level="INFO"
            ) as logger:
                send_queue.send_message(self.test_file_path, test_args)
            mock_conn.connect.assert_called_once_with(
                test_args["username"], test_args["password"], wait=True
            )
            mock_conn.set_ssl.assert_not_called()
            self.assertIn(
                "INFO:hepbenchmarksuite.plugins.send_queue:AMQ Plain: user-password based authentication",
                logger.output,
            )
            self.assertIn(
                "INFO:hepbenchmarksuite.plugins.send_queue:Sending results to AMQ topic",
                logger.output,
            )
            mock_conn.send.assert_called_once_with(
                test_args["topic"], "{'test':1}", "application/json"
            )
            mock_conn.disconnect.assert_called()
            mock_json.reset_mock()
            mock_stomp.reset_mock()
            mock_conn.reset_mock()

            # Test cert/key
            test_args = {
                "port": 8181,
                "server": "home.cern",
                "topic": "test",
                "cert": "somecert",
                "key": "somekey",
            }
            with self.assertLogs(
                "hepbenchmarksuite.plugins.send_queue", level="INFO"
            ) as logger:
                send_queue.send_message(self.test_file_path, test_args)
            mock_conn.set_ssl.assert_called_once_with(
                for_hosts=[(test_args["server"], test_args["port"])],
                cert_file=test_args["cert"],
                key_file=test_args["key"],
                ssl_version=5,
            )
            mock_conn.connect.assert_called_once_with(wait=True)
            self.assertIn(
                "INFO:hepbenchmarksuite.plugins.send_queue:AMQ SSL: certificate based authentication",
                logger.output,
            )
            self.assertIn(
                "INFO:hepbenchmarksuite.plugins.send_queue:Sending results to AMQ topic",
                logger.output,
            )
            mock_conn.send.assert_called_once_with(
                test_args["topic"], "{'test':1}", "application/json"
            )
            mock_conn.get_listener.assert_called_once_with("mylistener")
            mock_conn.disconnect.assert_called()

            mock_conn.get_listener("mylistener").configure_mock(status=False)
            with self.assertRaises(Exception):
                send_queue.send_message(self.test_file_path, test_args)

    def test_listener(self):
        """TODO(anyone): listener function"""
        # needs implementation of AsyncMock() to test
        # assert_awaited() etc
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
