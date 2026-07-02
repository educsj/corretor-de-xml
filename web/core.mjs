export const SEM_GTIN = "SEM GTIN";
export const DEFAULT_CPROD_DIGITS = 4;
export const MIN_RANDOM_CPROD_DIGITS = 4;
export const MAX_CPROD_DIGITS = 20;

const WINDOWS_1252_ENCODE = new Map([
  [0x20ac, 0x80],
  [0x201a, 0x82],
  [0x0192, 0x83],
  [0x201e, 0x84],
  [0x2026, 0x85],
  [0x2020, 0x86],
  [0x2021, 0x87],
  [0x02c6, 0x88],
  [0x2030, 0x89],
  [0x0160, 0x8a],
  [0x2039, 0x8b],
  [0x0152, 0x8c],
  [0x017d, 0x8e],
  [0x2018, 0x91],
  [0x2019, 0x92],
  [0x201c, 0x93],
  [0x201d, 0x94],
  [0x2022, 0x95],
  [0x2013, 0x96],
  [0x2014, 0x97],
  [0x02dc, 0x98],
  [0x2122, 0x99],
  [0x0161, 0x9a],
  [0x203a, 0x9b],
  [0x0153, 0x9c],
  [0x017e, 0x9e],
  [0x0178, 0x9f],
]);
const WINDOWS_1252_DECODE = new Map(
  [...WINDOWS_1252_ENCODE].map(([codePoint, byte]) => [byte, codePoint]),
);

export function correctXmlText(xmlText, options) {
  const normalized = normalizeOptions(options);
  if (!normalized.fixCEAN && !normalized.fixCEANTrib && normalized.cprodMode === "none") {
    throw new Error("Selecione ao menos uma correcao antes de gerar o XML.");
  }

  let output = xmlText;
  const changedCounts = { cEAN: 0, cEANTrib: 0, cProd: 0 };
  const foundCounts = { cEAN: 0, cEANTrib: 0, cProd: 0 };

  if (normalized.fixCEAN) {
    const result = replaceTagValue(output, "cEAN", normalized.semGtinText);
    output = result.xmlText;
    changedCounts.cEAN = result.changed;
    foundCounts.cEAN = result.found;
  }

  if (normalized.fixCEANTrib) {
    const result = replaceTagValue(output, "cEANTrib", normalized.semGtinText);
    output = result.xmlText;
    changedCounts.cEANTrib = result.changed;
    foundCounts.cEANTrib = result.found;
  }

  if (normalized.cprodMode === "sequential") {
    const result = renumberTagSequentially(output, "cProd", normalized.cprodDigits);
    output = result.xmlText;
    changedCounts.cProd = result.changed;
    foundCounts.cProd = result.found;
  } else if (normalized.cprodMode === "random") {
    const result = renumberTagRandomly(output, "cProd", normalized.cprodDigits);
    output = result.xmlText;
    changedCounts.cProd = result.changed;
    foundCounts.cProd = result.found;
  }

  return {
    xmlText: output,
    changedCounts,
    foundCounts,
    totalChanged: Object.values(changedCounts).reduce((total, count) => total + count, 0),
  };
}

export function detectXmlEncoding(input) {
  const bytes = asUint8Array(input);
  if (startsWith(bytes, [0xef, 0xbb, 0xbf])) {
    return { encoding: "utf-8", bom: true };
  }
  if (startsWith(bytes, [0xff, 0xfe])) {
    return { encoding: "utf-16le", bom: true };
  }
  if (startsWith(bytes, [0xfe, 0xff])) {
    return { encoding: "utf-16be", bom: true };
  }
  if (startsWith(bytes, [0x3c, 0x00, 0x3f, 0x00])) {
    return { encoding: "utf-16le", bom: false };
  }
  if (startsWith(bytes, [0x00, 0x3c, 0x00, 0x3f])) {
    return { encoding: "utf-16be", bom: false };
  }

  const head = String.fromCharCode(...bytes.slice(0, 512));
  const match = head.match(/<\?xml[^>]*encoding=["']([^"']+)["']/i);
  return {
    encoding: normalizeEncodingLabel(match?.[1] ?? "utf-8"),
    bom: false,
  };
}

export function decodeXmlBytes(input, encodingInfo = detectXmlEncoding(input)) {
  const bytes = asUint8Array(input);
  if (encodingInfo.encoding === "windows-1252") {
    return decodeWindows1252(bytes);
  }
  const decoder = new TextDecoder(encodingInfo.encoding, { fatal: true });
  return decoder.decode(bytes);
}

export function encodeXmlText(xmlText, encodingInfo) {
  let payload;
  if (encodingInfo.encoding === "utf-8") {
    payload = new TextEncoder().encode(xmlText);
  } else if (encodingInfo.encoding === "utf-16le") {
    payload = encodeUtf16(xmlText, true);
  } else if (encodingInfo.encoding === "utf-16be") {
    payload = encodeUtf16(xmlText, false);
  } else if (encodingInfo.encoding === "windows-1252") {
    payload = encodeWindows1252(xmlText);
  } else {
    throw new Error(`Codificacao XML nao suportada na versao web: ${encodingInfo.encoding}`);
  }

  if (!encodingInfo.bom) {
    return payload;
  }
  if (encodingInfo.encoding === "utf-8") {
    return concatBytes(new Uint8Array([0xef, 0xbb, 0xbf]), payload);
  }
  if (encodingInfo.encoding === "utf-16le") {
    return concatBytes(new Uint8Array([0xff, 0xfe]), payload);
  }
  if (encodingInfo.encoding === "utf-16be") {
    return concatBytes(new Uint8Array([0xfe, 0xff]), payload);
  }
  return payload;
}

export function buildOutputName(inputName) {
  const name = inputName || "nota.xml";
  const lastDot = name.lastIndexOf(".");
  const stem = lastDot > 0 ? name.slice(0, lastDot) : name;
  const extension = lastDot > 0 ? name.slice(lastDot) : ".xml";
  return `${stem}_corrigido${extension.toLowerCase() === ".xml" ? extension : ".xml"}`;
}

function normalizeOptions(options = {}) {
  const cprodMode = options.cprodMode ?? "none";
  const cprodDigits = Number(options.cprodDigits ?? DEFAULT_CPROD_DIGITS);
  if (!["none", "sequential", "random"].includes(cprodMode)) {
    throw new Error("Modo de correcao do cProd invalido.");
  }
  if (!Number.isInteger(cprodDigits) || cprodDigits < 1 || cprodDigits > MAX_CPROD_DIGITS) {
    throw new Error(`A quantidade de digitos do cProd deve ficar entre 1 e ${MAX_CPROD_DIGITS}.`);
  }
  if (cprodMode === "random" && cprodDigits < MIN_RANDOM_CPROD_DIGITS) {
    throw new Error(
      `Os codigos aleatorios do cProd devem ter ao menos ${MIN_RANDOM_CPROD_DIGITS} digitos.`,
    );
  }
  return {
    fixCEAN: Boolean(options.fixCEAN),
    fixCEANTrib: Boolean(options.fixCEANTrib),
    cprodMode,
    cprodDigits,
    semGtinText: options.semGtinText ?? SEM_GTIN,
  };
}

function replaceTagValue(xmlText, tagName, value) {
  let changed = 0;
  let found = 0;
  const xml = xmlText.replace(tagPattern(tagName), (...args) => {
    const groups = args.at(-1);
    found += 1;
    if (groups.value !== value) {
      changed += 1;
    }
    return `${groups.open}${value}${groups.close}`;
  });
  return { xmlText: xml, changed, found };
}

function renumberTagSequentially(xmlText, tagName, digits) {
  let changed = 0;
  let found = 0;
  const xml = xmlText.replace(tagPattern(tagName), (...args) => {
    const groups = args.at(-1);
    found += 1;
    const nextValue = String(found).padStart(digits, "0");
    if (groups.value !== nextValue) {
      changed += 1;
    }
    return `${groups.open}${nextValue}${groups.close}`;
  });
  return { xmlText: xml, changed, found };
}

function renumberTagRandomly(xmlText, tagName, digits) {
  const matches = [...xmlText.matchAll(tagPattern(tagName))];
  const found = matches.length;
  if (!found) {
    return { xmlText, changed: 0, found: 0 };
  }

  const originalValues = new Set(matches.map((match) => match.groups.value));
  const validOriginals = [...originalValues].filter(
    (value) => value.length === digits && /^[1-9]\d+$/.test(value),
  );
  const capacity = 9n * 10n ** BigInt(digits - 1);
  if (BigInt(found) > capacity - BigInt(validOriginals.length)) {
    throw new Error(
      `Nao ha codigos aleatorios de ${digits} digitos suficientes para ${found} itens.`,
    );
  }

  const usedValues = new Set(originalValues);
  const generatedValues = [];
  while (generatedValues.length < found) {
    const candidate = randomNumericCode(digits);
    if (usedValues.has(candidate)) {
      continue;
    }
    usedValues.add(candidate);
    generatedValues.push(candidate);
  }

  let index = 0;
  const xml = xmlText.replace(tagPattern(tagName), (...args) => {
    const groups = args.at(-1);
    const nextValue = generatedValues[index];
    index += 1;
    return `${groups.open}${nextValue}${groups.close}`;
  });
  return { xmlText: xml, changed: found, found };
}

function randomNumericCode(digits) {
  let value = String(1 + secureRandomInteger(9));
  for (let index = 1; index < digits; index += 1) {
    value += String(secureRandomInteger(10));
  }
  return value;
}

function secureRandomInteger(maxExclusive) {
  if (!globalThis.crypto?.getRandomValues) {
    throw new Error("O navegador nao oferece um gerador seguro de numeros aleatorios.");
  }
  const limit = Math.floor(256 / maxExclusive) * maxExclusive;
  const data = new Uint8Array(1);
  do {
    globalThis.crypto.getRandomValues(data);
  } while (data[0] >= limit);
  return data[0] % maxExclusive;
}

function tagPattern(tagName) {
  const escapedTag = escapeRegExp(tagName);
  return new RegExp(
    `(?<open><(?<prefix>(?:[A-Za-z_][\\w.-]*:)?)${escapedTag}\\b[^>]*>)` +
      `(?<value>.*?)(?<close></\\k<prefix>${escapedTag}>)`,
    "gs",
  );
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function normalizeEncodingLabel(label) {
  const normalized = label.trim().toLowerCase().replaceAll("_", "-");
  if (["utf-8", "utf8"].includes(normalized)) {
    return "utf-8";
  }
  if (["utf-16", "utf-16le"].includes(normalized)) {
    return "utf-16le";
  }
  if (normalized === "utf-16be") {
    return "utf-16be";
  }
  if (
    ["iso-8859-1", "iso8859-1", "latin1", "windows-1252", "cp1252"].includes(normalized)
  ) {
    return "windows-1252";
  }
  throw new Error(`Codificacao XML nao suportada na versao web: ${label}`);
}

function encodeUtf16(text, littleEndian) {
  const output = new Uint8Array(text.length * 2);
  for (let index = 0; index < text.length; index += 1) {
    const codeUnit = text.charCodeAt(index);
    const offset = index * 2;
    output[offset] = littleEndian ? codeUnit & 0xff : codeUnit >> 8;
    output[offset + 1] = littleEndian ? codeUnit >> 8 : codeUnit & 0xff;
  }
  return output;
}

function encodeWindows1252(text) {
  const values = [];
  for (const character of text) {
    const codePoint = character.codePointAt(0);
    if (WINDOWS_1252_ENCODE.has(codePoint)) {
      values.push(WINDOWS_1252_ENCODE.get(codePoint));
    } else if (codePoint <= 0xff) {
      values.push(codePoint);
    } else {
      throw new Error(
        `O caractere ${character} nao pode ser salvo na codificacao Windows-1252 original.`,
      );
    }
  }
  return new Uint8Array(values);
}

function decodeWindows1252(bytes) {
  return [...bytes]
    .map((byte) => String.fromCodePoint(WINDOWS_1252_DECODE.get(byte) ?? byte))
    .join("");
}

function concatBytes(prefix, payload) {
  const output = new Uint8Array(prefix.length + payload.length);
  output.set(prefix, 0);
  output.set(payload, prefix.length);
  return output;
}

function startsWith(bytes, prefix) {
  return prefix.every((value, index) => bytes[index] === value);
}

function asUint8Array(input) {
  return input instanceof Uint8Array ? input : new Uint8Array(input);
}
