import pytest
from app import schemas


@pytest.mark.parametrize("color", ["000000", "FFFFFF", "012e34", "abFc12", "123456"])
def test_validate_color(color):
    assert schemas.validate_color(color) == color


@pytest.mark.parametrize("color", ["", "blue", "#FFFFFF", "#012345", "00000000", "FFF"])
def test_validate_color_invalid(color):
    with pytest.raises(ValueError):
        schemas.validate_color(color)
