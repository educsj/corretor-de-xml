# Corretor de XML NF-e

Aplicativo Windows para corrigir XMLs de notas fiscais de entrada antes da importacao em sistemas ERP.

## Versao web

Acesse sem instalar:

<https://educsj.github.io/corretor-de-xml/>

O XML e processado inteiramente no navegador. Nenhum conteudo da nota e
enviado para um servidor.

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
- Gera numeros aleatorios unicos para `<cProd>`, com no minimo 4 digitos.
- Permite alterar a quantidade de digitos do `<cProd>`.
- Inclui um manual de uso dentro do proprio programa.
- Interface grafica simples para Windows.
- Pacote executavel para Linux x86_64.
- Versao web responsiva, sem instalacao.

## Como usar

1. Abra `CorretorXMLNFe.exe`.
2. Clique em **Selecionar** e escolha o XML da nota.
3. Escolha o erro/correcao desejado.
4. Clique em **Gerar XML corrigido**.
5. Importe no ERP o arquivo gerado com sufixo `_corrigido`.

## Executavel

O executavel para Windows fica disponivel nas releases do projeto:

<https://github.com/educsj/corretor-de-xml/releases>

Cada release tambem inclui:

- `CorretorXMLNFe-linux-x86_64.tar.gz`: pacote para Linux.
- `Manual_Corretor_XML_NFe.docx`: manual em Word.
- `SHA256SUMS.txt`: checksums para conferir os downloads.

## Executar no Linux

Extraia o pacote:

```bash
tar -xzf CorretorXMLNFe-linux-x86_64.tar.gz
```

Permita a execucao e abra o programa:

```bash
chmod +x CorretorXMLNFe-linux-x86_64
./CorretorXMLNFe-linux-x86_64
```

O pacote e compilado no Ubuntu 22.04 e destinado a distribuicoes Linux x86_64
recentes com ambiente grafico.

## Aviso do Windows

O executavel atual ainda nao possui assinatura digital de editor. Por isso,
o Microsoft Defender SmartScreen pode exibir um aviso de aplicativo nao
reconhecido, especialmente em uma versao nova. Baixe somente pelas releases
oficiais e confira o checksum publicado.

Para distribuicao em maior escala, a mitigacao recomendada e assinar todas as
versoes com a mesma identidade de editor ou publicar pela Microsoft Store.

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
node --test web/tests/core.test.mjs
```

## Rodar a versao web localmente

```powershell
python -m http.server 8000 --directory web
```

Abra <http://localhost:8000>.

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
