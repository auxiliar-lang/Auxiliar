# Auxiliar

Programa para Windows 11 que funciona como uma planilha de lançamentos:
**data, descrição, valor e comprovante** (JPG, PNG ou PDF).

## Como usar
1. Abra o repositório no GitHub → aba **Actions** → último "Gerar executável" → baixe **Planilha-windows**.
2. Descompacte e coloque `Planilha.exe` numa pasta onde você possa salvar arquivos (ex.: Documentos).
3. Ao abrir, o programa cria a pasta `dados/` ao lado dele, com o banco (`planilha.db`) e os comprovantes.

- Duplo clique numa célula de data, descrição ou valor edita direto na tabela (Enter confirma, Esc cancela).
- Duplo clique na coluna Comprovante abre o arquivo.
- Para fazer backup, copie a pasta `dados/` inteira.

## Windows pode avisar
O `.exe` não tem assinatura digital. Se o SmartScreen bloquear: **Mais informações → Executar assim mesmo**.

## Desenvolvimento
```
python app.py
python -m unittest discover -s tests -v
```
