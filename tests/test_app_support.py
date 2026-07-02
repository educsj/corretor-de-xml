from pathlib import Path

from nfe_xml_corrector.app import folder_open_command
from nfe_xml_corrector.manual import APP_VERSION, MANUAL_SECTIONS


def test_folder_open_command_is_platform_specific() -> None:
    folder = Path("/tmp/notas")

    assert folder_open_command("win32", folder) is None
    assert folder_open_command("darwin", folder) == ["open", str(folder)]
    assert folder_open_command("linux", folder) == ["xdg-open", str(folder)]


def test_integrated_manual_covers_every_correction_mode() -> None:
    manual_text = "\n".join(
        f"{heading}\n{body}" for heading, body in MANUAL_SECTIONS
    )

    assert APP_VERSION == "0.3.0"
    assert "<cEAN>" in manual_text
    assert "<cEANTrib>" in manual_text
    assert "<cProd>" in manual_text
    assert "sequencia" in manual_text
    assert "aleatorios unicos" in manual_text
    assert "Linux" in manual_text
