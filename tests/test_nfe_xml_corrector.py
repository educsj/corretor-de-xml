from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from nfe_xml_corrector.core import (
    CorrectionOptions,
    correct_xml_file,
    default_output_path,
)


SAMPLE_NFE = """<?xml version="1.0" encoding="UTF-8"?>
<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
  <infNFe>
    <det nItem="1">
      <prod>
        <cProd>ABC#1</cProd>
        <cEAN>789100000001</cEAN>
        <cEANTrib>789100000001</cEANTrib>
      </prod>
    </det>
    <det nItem="2">
      <prod>
        <cProd>XYZ/2</cProd>
        <cEAN>789100000002</cEAN>
        <cEANTrib>789100000002</cEANTrib>
      </prod>
    </det>
  </infNFe>
</NFe>
"""

SAMPLE_NFE_PROC = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe xmlns="http://www.portalfiscal.inf.br/nfe">
    <infNFe versao="4.00" Id="NFe123">
      <det nItem="1">
        <prod>
          <cProd>139068</cProd>
          <cEAN>7896045503414</cEAN>
          <xProd>KAISER LT 473 ML 12 pack</xProd>
          <cEANTrib>7896045503414</cEANTrib>
        </prod>
      </det>
    </infNFe>
  </NFe>
</nfeProc>
"""


def test_fix_cean_keeps_ceantrib_when_not_selected(tmp_path: Path) -> None:
    input_file = tmp_path / "nota.xml"
    output_file = tmp_path / "nota_corrigida.xml"
    input_file.write_text(SAMPLE_NFE, encoding="utf-8")

    result = correct_xml_file(
        input_file,
        output_file,
        CorrectionOptions(fix_cean=True),
    )

    values = _values_by_tag(result.output_path)
    assert values["cEAN"] == ["SEM GTIN", "SEM GTIN"]
    assert values["cEANTrib"] == ["789100000001", "789100000002"]
    assert result.changed_counts["cEAN"] == 2
    assert result.found_counts["cEAN"] == 2


def test_fix_ceantrib_when_selected(tmp_path: Path) -> None:
    input_file = tmp_path / "nota.xml"
    output_file = tmp_path / "nota_corrigida.xml"
    input_file.write_text(SAMPLE_NFE, encoding="utf-8")

    result = correct_xml_file(
        input_file,
        output_file,
        CorrectionOptions(fix_cean=True, fix_ceantrib=True),
    )

    values = _values_by_tag(result.output_path)
    assert values["cEAN"] == ["SEM GTIN", "SEM GTIN"]
    assert values["cEANTrib"] == ["SEM GTIN", "SEM GTIN"]
    assert result.changed_counts["cEANTrib"] == 2


def test_renumber_cprod_uses_four_digits_in_item_order(tmp_path: Path) -> None:
    input_file = tmp_path / "nota.xml"
    output_file = tmp_path / "nota_corrigida.xml"
    input_file.write_text(SAMPLE_NFE, encoding="utf-8")

    result = correct_xml_file(
        input_file,
        output_file,
        CorrectionOptions(renumber_cprod=True),
    )

    values = _values_by_tag(result.output_path)
    assert values["cProd"] == ["0001", "0002"]
    assert result.changed_counts["cProd"] == 2
    assert result.found_counts["cProd"] == 2


def test_renumber_cprod_allows_custom_digit_count(tmp_path: Path) -> None:
    input_file = tmp_path / "nota.xml"
    output_file = tmp_path / "nota_corrigida.xml"
    input_file.write_text(SAMPLE_NFE, encoding="utf-8")

    correct_xml_file(
        input_file,
        output_file,
        CorrectionOptions(renumber_cprod=True, cprod_digits=7),
    )

    values = _values_by_tag(output_file)
    assert values["cProd"] == ["0000001", "0000002"]


def test_combined_corrections(tmp_path: Path) -> None:
    input_file = tmp_path / "nota.xml"
    output_file = tmp_path / "nota_corrigida.xml"
    input_file.write_text(SAMPLE_NFE, encoding="utf-8")

    correct_xml_file(
        input_file,
        output_file,
        CorrectionOptions(fix_cean=True, renumber_cprod=True),
    )

    values = _values_by_tag(output_file)
    assert values["cEAN"] == ["SEM GTIN", "SEM GTIN"]
    assert values["cProd"] == ["0001", "0002"]


def test_preserves_xml_markup_and_changes_only_requested_tags(tmp_path: Path) -> None:
    input_file = tmp_path / "nota.xml"
    output_file = tmp_path / "nota_corrigida.xml"
    input_file.write_text(SAMPLE_NFE_PROC, encoding="utf-8")

    correct_xml_file(
        input_file,
        output_file,
        CorrectionOptions(fix_cean=True, fix_ceantrib=True, renumber_cprod=True),
    )

    expected = (
        SAMPLE_NFE_PROC
        .replace("<cProd>139068</cProd>", "<cProd>0001</cProd>")
        .replace("<cEAN>7896045503414</cEAN>", "<cEAN>SEM GTIN</cEAN>")
        .replace("<cEANTrib>7896045503414</cEANTrib>", "<cEANTrib>SEM GTIN</cEANTrib>")
    )
    output_text = output_file.read_text(encoding="utf-8")
    assert output_text == expected
    assert "ns0:" not in output_text
    assert '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">' in output_text
    assert "<xProd>KAISER LT 473 ML 12 pack</xProd>" in output_text


def test_requires_at_least_one_correction(tmp_path: Path) -> None:
    input_file = tmp_path / "nota.xml"
    output_file = tmp_path / "nota_corrigida.xml"
    input_file.write_text(SAMPLE_NFE, encoding="utf-8")

    with pytest.raises(ValueError, match="Selecione ao menos uma correcao"):
        correct_xml_file(input_file, output_file, CorrectionOptions())


def test_default_output_path_adds_suffix(tmp_path: Path) -> None:
    input_file = tmp_path / "nota.xml"
    input_file.write_text(SAMPLE_NFE, encoding="utf-8")

    assert default_output_path(input_file) == tmp_path / "nota_corrigido.xml"


def _values_by_tag(path: Path) -> dict[str, list[str]]:
    root = ET.parse(path).getroot()
    values: dict[str, list[str]] = {"cProd": [], "cEAN": [], "cEANTrib": []}
    for element in root.iter():
        local = _local_name(element.tag)
        if local in values:
            values[local].append(element.text or "")
    return values


def _local_name(tag: str) -> str:
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[1]
    return tag
