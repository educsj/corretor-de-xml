from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import xml.etree.ElementTree as ET


SEM_GTIN = "SEM GTIN"
DEFAULT_CPROD_DIGITS = 4


@dataclass(frozen=True)
class CorrectionOptions:
    fix_cean: bool = False
    fix_ceantrib: bool = False
    renumber_cprod: bool = False
    cprod_digits: int = DEFAULT_CPROD_DIGITS
    sem_gtin_text: str = SEM_GTIN


@dataclass(frozen=True)
class CorrectionResult:
    input_path: Path
    output_path: Path
    changed_counts: dict[str, int] = field(default_factory=dict)
    found_counts: dict[str, int] = field(default_factory=dict)

    @property
    def total_changed(self) -> int:
        return sum(self.changed_counts.values())


def default_output_path(input_path: str | Path) -> Path:
    """Return a non-conflicting output path beside the original XML."""
    path = Path(input_path)
    candidate = path.with_name(f"{path.stem}_corrigido{path.suffix}")
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_corrigido_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def correct_xml_file(
    input_path: str | Path,
    output_path: str | Path,
    options: CorrectionOptions,
) -> CorrectionResult:
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {input_file}")
    if not input_file.is_file():
        raise ValueError(f"O caminho de entrada nao e um arquivo: {input_file}")
    if not _has_any_option(options):
        raise ValueError("Selecione ao menos uma correcao antes de gerar o XML.")
    if options.cprod_digits < 1:
        raise ValueError("A quantidade de digitos do cProd deve ser maior que zero.")

    _register_namespaces(input_file)
    tree = ET.parse(input_file)
    root = tree.getroot()

    changed_counts = {"cEAN": 0, "cEANTrib": 0, "cProd": 0}
    found_counts = {"cEAN": 0, "cEANTrib": 0, "cProd": 0}

    if options.fix_cean:
        changed, found = _set_product_tag(root, "cEAN", options.sem_gtin_text)
        changed_counts["cEAN"] = changed
        found_counts["cEAN"] = found

    if options.fix_ceantrib:
        changed, found = _set_product_tag(root, "cEANTrib", options.sem_gtin_text)
        changed_counts["cEANTrib"] = changed
        found_counts["cEANTrib"] = found

    if options.renumber_cprod:
        changed, found = _renumber_cprod(root, options.cprod_digits)
        changed_counts["cProd"] = changed
        found_counts["cProd"] = found

    output_file.parent.mkdir(parents=True, exist_ok=True)
    encoding = _detect_xml_encoding(input_file)
    tree.write(output_file, encoding=encoding, xml_declaration=True)

    return CorrectionResult(
        input_path=input_file,
        output_path=output_file,
        changed_counts=changed_counts,
        found_counts=found_counts,
    )


def _has_any_option(options: CorrectionOptions) -> bool:
    return options.fix_cean or options.fix_ceantrib or options.renumber_cprod


def _detect_xml_encoding(path: Path) -> str:
    head = path.read_bytes()[:256]
    match = re.search(br"<\?xml[^>]*encoding=[\"']([^\"']+)[\"']", head, re.I)
    if not match:
        return "utf-8"
    try:
        return match.group(1).decode("ascii")
    except UnicodeDecodeError:
        return "utf-8"


def _register_namespaces(path: Path) -> None:
    seen: set[tuple[str, str]] = set()
    try:
        for _event, namespace in ET.iterparse(path, events=("start-ns",)):
            prefix, uri = namespace
            item = (prefix or "", uri)
            if item in seen:
                continue
            seen.add(item)
            try:
                ET.register_namespace(prefix or "", uri)
            except ValueError:
                # Reserved prefixes are already known by ElementTree.
                continue
    except ET.ParseError:
        raise


def _local_name(tag: str) -> str:
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[1]
    return tag


def _first_direct_child(parent: ET.Element, local_name: str) -> ET.Element | None:
    for child in list(parent):
        if _local_name(child.tag) == local_name:
            return child
    return None


def _product_elements(root: ET.Element) -> list[ET.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == "prod"]


def _set_product_tag(root: ET.Element, local_name: str, value: str) -> tuple[int, int]:
    changed = 0
    found = 0
    for product in _product_elements(root):
        element = _first_direct_child(product, local_name)
        if element is None:
            continue

        found += 1
        if (element.text or "") != value:
            element.text = value
            changed += 1

    return changed, found


def _renumber_cprod(root: ET.Element, digits: int) -> tuple[int, int]:
    changed = 0
    found = 0
    for index, cprod in enumerate(_cprod_elements_in_item_order(root), start=1):
        found += 1
        new_value = str(index).zfill(digits)
        if (cprod.text or "") != new_value:
            cprod.text = new_value
            changed += 1

    return changed, found


def _cprod_elements_in_item_order(root: ET.Element) -> list[ET.Element]:
    cprod_elements: list[ET.Element] = []
    seen: set[int] = set()

    for det in root.iter():
        if _local_name(det.tag) != "det":
            continue
        product = _first_direct_child(det, "prod")
        if product is None:
            continue
        cprod = _first_direct_child(product, "cProd")
        if cprod is None:
            continue
        cprod_elements.append(cprod)
        seen.add(id(cprod))

    for product in _product_elements(root):
        cprod = _first_direct_child(product, "cProd")
        if cprod is not None and id(cprod) not in seen:
            cprod_elements.append(cprod)

    return cprod_elements
