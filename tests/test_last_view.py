import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.layout import create_main_layout


def deck_value(component):
    if getattr(component, 'id', None) == 'deck-filter':
        return component.value
    children = getattr(component, 'children', None)
    for child in children if isinstance(children, list) else [children]:
        if child is not None:
            value = deck_value(child)
            if value is not None:
                return value
    return None


class LastViewTest(unittest.TestCase):
    def test_layout_restores_deck_and_handles_missing_deck(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'last_view.json'
            with patch('src.config.LAST_VIEW_FILE', str(path)), patch(
                'src.layout.get_deck_list', return_value=[{'id': 42, 'name': 'French'}]
            ):
                path.write_text(json.dumps(['42', '30', 'dates']))
                self.assertEqual(deck_value(create_main_layout()), '42')

                path.write_text(json.dumps(['99', '30', 'dates']))
                self.assertEqual(deck_value(create_main_layout()), 'all')

                path.write_text('invalid json')
                self.assertEqual(deck_value(create_main_layout()), 'all')


if __name__ == '__main__':
    unittest.main()
