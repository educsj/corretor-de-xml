# Corretor de XML NF-e

Aplicativo Windows para corrigir XMLs de notas fiscais de entrada antes da importacao em sistemas ERP.

O programa foi criado para resolver dois problemas comuns:

- Fornecedores enviando `<cEAN>` com EAN/GTIN que ja existe em outro produto.
- Fornecedores enviando `<cProd>` com caracteres ou formatos que geram erro de unicidade no ERP, como `SequelizeUniqueConstraintError`.

## Funcionalidades

- Importa um arquivo `.xml` de NF-e.
- Gera uma copia corrigida, sem alterar o XML original.
- Preserva a estrutura, formatacao e namespaces do XML original.
- Troca `<cEAN>` para `SEM GTIN`.
- Opcionalmente troca `<cEANTrib>` para `SEM GTIN`.
- Renumera `<cProd>` em sequencia: `0001`, `0002`, `0003`...
- Permite alterar a quantidade de digitos do `<cProd>`.
- Interface grafica simples para Windows.

## Como usar

1. Abra `CorretorXMLNFe.exe`.
2. Clique em **Selecionar** e escolha o XML da nota.
3. Escolha o erro/correcao desejado.
4. Clique em **Gerar XML corrigido**.
5. Importe no ERP o arquivo gerado com sufixo `_corrigido`.

## Executavel

O executavel para Windows fica disponivel nas releases do projeto:

<https://github.com/educsj/corretor-de-xml/releases>

## Rodar em modo desenvolvimento

Requisitos:

- Python 3.11 ou superior

Execute:

```powershell
python -m nfe_xml_corrector.app
```

## Rodar testes

Instale as dependencias de desenvolvimento:

```powershell
python -m pip install -r requirements-dev.txt
```

Depois rode:

```powershell
python -m pytest tests/test_nfe_xml_corrector.py -q
```

## Gerar o executavel

Instale as dependencias:

```powershell
python -m pip install -r requirements-dev.txt
```

Gere o `.exe`:

```powershell
powershell -ExecutionPolicy Bypass -File .\nfe_xml_corrector\build_exe.ps1
```

O arquivo sera criado em:

```text
dist\CorretorXMLNFe.exe
```

## Autor

Criado por [Eduardo Coutinho da Silva Junior](https://github.com/educsj).
