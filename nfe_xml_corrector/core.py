from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


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

    original_bytes = input_file.read_bytes()
    encoding = _detect_xml_encoding(original_bytes)
    xml_text = original_bytes.decode(encoding)

    changed_counts = {"cEAN": 0, "cEANTrib": 0, "cProd": 0}
    found_counts = {"cEAN": 0, "cEANTrib": 0, "cProd": 0}

    if options.fix_cean:
        xml_text, changed, found = _replace_tag_value(
            xml_text,
            "cEAN",
            options.sem_gtin_text,
        )
        changed_counts["cEAN"] = changed
        found_counts["cEAN"] = found

    if options.fix_ceantrib:
        xml_text, changed, found = _replace_tag_value(
            xml_text,
            "cEANTrib",
            options.sem_gtin_text,
        )
        changed_counts["cEANTrib"] = changed
        found_counts["cEANTrib"] = found

    if options.renumber_cprod:
        xml_text, changed, found = _renumber_tag_sequentially(
            xml_text,
            "cProd",
            options.cprod_digits,
        )
        changed_counts["cProd"] = changed
        found_counts["cProd"] = found

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(xml_text.encode(encoding))

    return CorrectionResult(
        input_path=input_file,
        output_path=output_file,
        changed_counts=changed_counts,
        found_counts=found_counts,
    )


def _has_any_option(options: CorrectionOptions) -> bool:
    return options.fix_cean or options.fix_ceantrib or options.renumber_cprod


def _detect_xml_encoding(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if data.startswith(b"\xff\xfe"):
        return "utf-16"
    if data.startswith(b"\xfe\xff"):
        return "utf-16"

    head = data[:256]
    match = re.search(br"<\?xml[^>]*encoding=[\"']([^\"']+)[\"']", head, re.I)
    if not match:
        return "utf-8"
    try:
        return match.group(1).decode("ascii")
    except UnicodeDecodeError:
        return "utf-8"


def _replace_tag_value(xml_text: str, tag_name: str, value: str) -> tuple[str, int, int]:
    changed = 0
    found = 0
    pattern = _tag_pattern(tag_name)

    def replace(match: re.Match[str]) -> str:
        nonlocal changed, found
        found += 1
        if match.group("value") != value:
            changed += 1
        return f"{match.group('open')}{value}{match.group('close')}"

    return pattern.sub(replace, xml_text), changed, found


def _renumber_tag_sequentially(xml_text: str, tag_name: str, digits: int) -> tuple[str, int, int]:
    changed = 0
    found = 0
    pattern = _tag_pattern(tag_name)

    def replace(match: re.Match[str]) -> str:
        nonlocal changed, found
        found += 1
        new_value = str(found).zfill(digits)
        if match.group("value") != new_value:
            changed += 1
        return f"{match.group('open')}{new_value}{match.group('close')}"

    return pattern.sub(replace, xml_text), changed, found


def _tag_pattern(tag_name: str) -> re.Pattern[str]:
    escaped_tag = re.escape(tag_name)
    return re.compile(
        rf"(?P<open><(?P<prefix>(?:[A-Za-z_][\w.-]*:)?)"
        rf"{escaped_tag}\b[^>]*>)"
        rf"(?P<value>.*?)"
        rf"(?P<close></(?P=prefix){escaped_tag}>)",
        re.DOTALL,
    )
