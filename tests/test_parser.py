import unittest
from parser import (
    _get_attribute, HubAttributeDuplicatesError, ValueRangeError
)
from zone import ZoneType


class TestGetAttribute(unittest.TestCase):

    # --- 正常系 ---

    def test_color_only(self) -> None:
        result = _get_attribute("color=green]", line_num=1)
        self.assertEqual(result, {"color": "green"})

    def test_max_drones_only(self) -> None:
        result = _get_attribute("max_drones=3]", line_num=1)
        self.assertEqual(result, {"max_drones": 3})

    def test_zone_type_only(self) -> None:
        result = _get_attribute("zone=restricted]", line_num=1)
        self.assertEqual(result, {"zone_type": ZoneType.RESTRICTED})

    def test_color_and_max_drones(self) -> None:
        result = _get_attribute("color=yellow max_drones=2]", line_num=1)
        self.assertEqual(result, {"color": "yellow", "max_drones": 2})

    def test_all_three_attributes(self) -> None:
        result = _get_attribute(
            "zone=restricted color=red max_drones=1]", line_num=1
        )
        self.assertEqual(result, {
            "zone_type": ZoneType.RESTRICTED,
            "color": "red",
            "max_drones": 1,
        })

    def test_empty_attributes(self) -> None:
        result = _get_attribute("]", line_num=1)
        self.assertEqual(result, {})

    # --- 異常系: 重複 ---

    def test_duplicate_color_raises(self) -> None:
        with self.assertRaises(HubAttributeDuplicatesError):
            _get_attribute("color=yellow color=red]", line_num=5)

    def test_duplicate_max_drones_raises(self) -> None:
        with self.assertRaises(HubAttributeDuplicatesError):
            _get_attribute("max_drones=2 max_drones=3]", line_num=5)

    def test_duplicate_zone_raises(self) -> None:
        with self.assertRaises(HubAttributeDuplicatesError):
            _get_attribute("zone=restricted zone=blocked]", line_num=5)

    # --- 異常系: 値の範囲 ---

    def test_max_drones_zero_allowed(self) -> None:
        result = _get_attribute("max_drones=0]", line_num=3)
        self.assertEqual(result, {"max_drones": 0})

    def test_max_drones_negative_raises(self) -> None:
        with self.assertRaises(ValueRangeError):
            _get_attribute("max_drones=-1]", line_num=3)

    # --- line_num がエラーに反映されるか ---

    def test_duplicate_error_has_correct_line_num(self) -> None:
        with self.assertRaises(HubAttributeDuplicatesError) as ctx:
            _get_attribute("color=yellow color=red]", line_num=7)
        self.assertEqual(ctx.exception.line_num, 7)


if __name__ == "__main__":
    unittest.main()
