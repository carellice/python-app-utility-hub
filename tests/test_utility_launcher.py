from pathlib import Path
import unittest
from unittest.mock import patch

import utility_launcher


class MacOSLaunchTests(unittest.TestCase):
    def test_frozen_utility_uses_launch_services_on_macos(self) -> None:
        """A child utility must be opened as a second .app instance on macOS."""
        hub = object.__new__(utility_launcher.UtilityHub)
        hub.selected_utility = lambda: utility_launcher.UTILITIES[0]
        hub.refresh_status = lambda: None
        app_bundle = Path("/Applications/Python App Utility Hub.app")

        with (
            patch("utility_launcher.is_frozen", return_value=True),
            patch("utility_launcher.macos_app_bundle", return_value=app_bundle),
            patch("utility_launcher.subprocess.Popen") as popen,
        ):
            hub.launch_selected()

        popen.assert_called_once_with(
            [
                "open",
                "-n",
                str(app_bundle),
                "--args",
                "--run-utility",
                "comic_tag_editor",
            ]
        )


if __name__ == "__main__":
    unittest.main()
