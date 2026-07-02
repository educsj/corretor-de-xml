APP_VERSION = "0.3.0"

MANUAL_SECTIONS = (
    (
        "Passo a passo",
        "1. Clique em Selecionar e escolha o XML da nota de entrada.\n"
        "2. No campo Erro do ERP, escolha a situacao mais parecida com o problema.\n"
        "3. Confira as correcoes marcadas e ajuste os digitos do cProd, se necessario.\n"
        "4. Clique em Gerar XML corrigido.\n"
        "5. A pasta do arquivo corrigido sera aberta automaticamente.\n"
        "6. Importe no ERP o arquivo com o sufixo _corrigido.",
    ),
    (
        "Quando usar cada correcao",
        "Trocar <cEAN> para SEM GTIN\n"
        "Use quando o EAN enviado pelo fornecedor faz o ERP vincular o item ao produto errado.\n\n"
        "Trocar tambem <cEANTrib> para SEM GTIN\n"
        "Marque quando o ERP tambem estiver validando o EAN tributavel. Em caso de duvida, "
        "tente primeiro apenas o cEAN.\n\n"
        "Renumerar <cProd> em sequencia\n"
        "Use para cProd com caracteres ou formatos que causam SequelizeUniqueConstraintError. "
        "Os itens ficam 0001, 0002, 0003 e assim por diante.\n\n"
        "Gerar numeros aleatorios unicos para <cProd>\n"
        "Use quando codigos sequenciais podem coincidir com produtos ja cadastrados no cliente. "
        "Os codigos nao se repetem dentro da nota. O minimo e 4 digitos; usar 6 ou 8 reduz "
        "a chance de coincidencia com o cadastro do ERP.",
    ),
    (
        "O que fazem os presets",
        "EAN vincula produto errado: marca somente a correcao de cEAN.\n"
        "SequelizeUniqueConstraintError / cProd: seleciona a numeracao em sequencia.\n"
        "cProd ja existe no cadastro: seleciona os numeros aleatorios.\n"
        "Corrigir EAN e cProd: combina cEAN com cProd em sequencia.\n"
        "Personalizado: aparece quando voce altera as opcoes manualmente.",
    ),
    (
        "Cuidados importantes",
        "O programa cria uma copia e nao altera o XML original.\n"
        "Somente as tags selecionadas sao modificadas.\n"
        "Guarde o XML original como backup.\n"
        "Depois da importacao, confirme no ERP se cada item foi vinculado ao produto correto.",
    ),
    (
        "Uso no Linux",
        "Extraia o arquivo .tar.gz da release. Se necessario, permita a execucao com:\n"
        "chmod +x CorretorXMLNFe-linux-x86_64\n\n"
        "Depois execute pelo gerenciador de arquivos ou pelo terminal:\n"
        "./CorretorXMLNFe-linux-x86_64",
    ),
)
