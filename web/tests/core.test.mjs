import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildOutputName,
  correctXmlText,
  decodeXmlBytes,
  detectXmlEncoding,
  encodeXmlText,
} from "../core.mjs";

const SAMPLE = `<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe>
      <det nItem="1"><prod>
        <cProd>ABC#1</cProd>
        <cEAN>789100000001</cEAN>
        <xProd>Produto um preservado</xProd>
        <cEANTrib>789100000001</cEANTrib>
      </prod></det>
      <det nItem="2"><prod>
        <cProd>XYZ/2</cProd>
        <cEAN>789100000002</cEAN>
        <xProd>Produto dois preservado</xProd>
        <cEANTrib>789100000002</cEANTrib>
      </prod></det>
    </infNFe>
  </NFe>
</nfeProc>
`;

test("corrige apenas cEAN quando essa e a unica opcao", () => {
  const result = correctXmlText(SAMPLE, { fixCEAN: true });

  assert.equal(result.changedCounts.cEAN, 2);
  assert.equal(result.changedCounts.cEANTrib, 0);
  assert.match(result.xmlText, /<cEAN>SEM GTIN<\/cEAN>/);
  assert.match(result.xmlText, /<cEANTrib>789100000001<\/cEANTrib>/);
  assert.match(result.xmlText, /<xProd>Produto um preservado<\/xProd>/);
  assert.doesNotMatch(result.xmlText, /ns0:/);
});

test("renumera cProd em sequencia com quatro digitos", () => {
  const result = correctXmlText(SAMPLE, {
    cprodMode: "sequential",
    cprodDigits: 4,
  });

  assert.deepEqual(
    [...result.xmlText.matchAll(/<cProd>(.*?)<\/cProd>/g)].map((match) => match[1]),
    ["0001", "0002"],
  );
  assert.equal(result.changedCounts.cProd, 2);
});

test("gera cProd aleatorios numericos e unicos", () => {
  const result = correctXmlText(SAMPLE, {
    cprodMode: "random",
    cprodDigits: 6,
  });
  const values = [...result.xmlText.matchAll(/<cProd>(.*?)<\/cProd>/g)].map(
    (match) => match[1],
  );

  assert.equal(values.length, 2);
  assert.equal(new Set(values).size, 2);
  assert.ok(values.every((value) => /^\d{6}$/.test(value)));
  assert.ok(values.every((value) => !["ABC#1", "XYZ/2"].includes(value)));
});

test("preserva prefixos de namespace existentes sem criar novos", () => {
  const prefixed = SAMPLE.replaceAll("<cEAN>", "<nfe:cEAN>")
    .replaceAll("</cEAN>", "</nfe:cEAN>")
    .replace("<nfeProc ", '<nfeProc xmlns:nfe="http://www.portalfiscal.inf.br/nfe" ');
  const result = correctXmlText(prefixed, { fixCEAN: true });

  assert.match(result.xmlText, /<nfe:cEAN>SEM GTIN<\/nfe:cEAN>/);
  assert.doesNotMatch(result.xmlText, /ns0:/);
});

test("processa nota grande com 300 itens", () => {
  const items = Array.from(
    { length: 300 },
    (_, index) =>
      `<det nItem="${index + 1}"><prod><cProd>FORN-${index + 1}</cProd>` +
      `<cEAN>789${String(index + 1).padStart(10, "0")}</cEAN>` +
      `<xProd>Produto ${index + 1}</xProd></prod></det>`,
  ).join("");
  const xml = `<?xml version="1.0" encoding="UTF-8"?><NFe>${items}</NFe>`;
  const result = correctXmlText(xml, {
    fixCEAN: true,
    cprodMode: "random",
    cprodDigits: 8,
  });
  const cprodValues = [...result.xmlText.matchAll(/<cProd>(.*?)<\/cProd>/g)].map(
    (match) => match[1],
  );

  assert.equal(result.changedCounts.cEAN, 300);
  assert.equal(result.changedCounts.cProd, 300);
  assert.equal(new Set(cprodValues).size, 300);
  assert.match(result.xmlText, /<xProd>Produto 300<\/xProd>/);
});

test("preserva UTF-8 com BOM", () => {
  const info = { encoding: "utf-8", bom: true };
  const bytes = encodeXmlText(SAMPLE, info);

  assert.deepEqual([...bytes.slice(0, 3)], [0xef, 0xbb, 0xbf]);
  assert.deepEqual(detectXmlEncoding(bytes), info);
  assert.equal(decodeXmlBytes(bytes), SAMPLE);
});

test("preserva UTF-16 little endian", () => {
  const info = { encoding: "utf-16le", bom: true };
  const text = SAMPLE.replace("UTF-8", "UTF-16");
  const bytes = encodeXmlText(text, info);

  assert.deepEqual(detectXmlEncoding(bytes), info);
  assert.equal(decodeXmlBytes(bytes), text);
});

test("preserva Windows-1252 com acentos", () => {
  const info = { encoding: "windows-1252", bom: false };
  const text = SAMPLE.replace("UTF-8", "windows-1252").replace("Produto um", "Ação €");
  const bytes = encodeXmlText(text, info);

  assert.deepEqual(detectXmlEncoding(bytes), info);
  assert.equal(decodeXmlBytes(bytes), text);
});

test("gera nome de saida sem substituir o original", () => {
  assert.equal(buildOutputName("nota.xml"), "nota_corrigido.xml");
  assert.equal(buildOutputName("entrada"), "entrada_corrigido.xml");
});
