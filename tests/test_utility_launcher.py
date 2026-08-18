import unittest
from unittest.mock import patch

import utility_launcher


class MacOSLaunchTests(unittest.TestCase):
    def test_frozen_utility_starts_a_child_with_its_arguments(self) -> None:
        """The frozen executable receives the selected utility key directly."""
        hub = object.__new__(utility_launcher.UtilityHub)
        hub.selected_utility = lambda: utility_launcher.UTILITIES[0]
        hub.refresh_status = lambda: None

        with (
            patch("utility_launcher.is_frozen", return_value=True),
            patch("utility_launcher.subprocess.Popen") as popen,
        ):
            hub.launch_selected()

        popen.assert_called_once_with(
            [utility_launcher.sys.executable, "--run-utility", "comic_tag_editor"]
        )


if __name__ == "__main__":
    unittest.main()
