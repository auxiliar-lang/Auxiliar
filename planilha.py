"""Lógica da planilha: validação, banco SQLite e cópia de comprovantes.

Este módulo não usa interface gráfica, para poder ser testado sozinho.
"""

import os
import shutil
import sqlite3
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

EXTENSOES_COMPROVANTE = (".jpg", ".jpeg", ".png", ".pdf")


def parse_data(texto):
    """Converte 'dd/mm/aaaa' para 'aaaa-mm-dd'. Levanta ValueError se inválida."""
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        raise ValueError("Data inválida. Use dd/mm/aaaa, por exemplo 05/11/2026.")


def formatar_data(iso):
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def parse_valor(texto):
    """Converte '1.234,56', '12,5' ou '10.5' para centavos (int)."""
    msg = "Valor inválido. Use números, por exemplo 1.234,56 ou 12,50."
    s = texto.strip().replace("R$", "").replace(" ", "")
    if not s:
        raise ValueError(msg)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(s)
    except InvalidOperation:
        raise ValueError(msg)
    if not numero.is_finite():
        raise ValueError(msg)
    centavos = numero * 100
    if centavos != centavos.to_integral_value():
        raise ValueError("Use no máximo 2 casas decimais no valor.")
    return int(centavos)


def formatar_valor(centavos):
    sinal = "-" if centavos < 0 else ""
    reais, resto = divmod(abs(centavos), 100)
    reais_txt = f"{reais:,}".replace(",", ".")
    return f"{sinal}R$ {reais_txt},{resto:02d}"


def valor_para_edicao(centavos):
    """Valor sem 'R$', para mostrar no campo de edição (ex.: 1234,56)."""
    sinal = "-" if centavos < 0 else ""
    reais, resto = divmod(abs(centavos), 100)
    return f"{sinal}{reais},{resto:02d}"


def nome_exibicao_comprovante(nome_guardado):
    """Remove o prefixo único que usamos para evitar nomes repetidos."""
    if not nome_guardado:
        return ""
    return nome_guardado.split("_", 1)[1] if "_" in nome_guardado else nome_guardado


class Planilha:
    CAMPOS_EDITAVEIS = {
        "data": ("data", parse_data),
        "descricao": ("descricao", lambda t: _validar_descricao(t)),
        "valor": ("valor_centavos", parse_valor),
    }

    def __init__(self, pasta_dados):
        self.pasta_comprovantes = os.path.join(pasta_dados, "comprovantes")
        os.makedirs(self.pasta_comprovantes, exist_ok=True)
        self.con = sqlite3.connect(os.path.join(pasta_dados, "planilha.db"))
        self.con.execute(
            """CREATE TABLE IF NOT EXISTS lancamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                descricao TEXT NOT NULL,
                valor_centavos INTEGER NOT NULL,
                comprovante TEXT
            )"""
        )
        self.con.commit()

    def adicionar(self, data_txt, descricao, valor_txt, comprovante_origem=None):
        # Valida tudo antes de copiar o arquivo, para não deixar cópia órfã.
        data_iso = parse_data(data_txt)
        descricao = _validar_descricao(descricao)
        centavos = parse_valor(valor_txt)
        _validar_comprovante(comprovante_origem)
        nome = self._copiar_comprovante(comprovante_origem) if comprovante_origem else None
        cur = self.con.execute(
            "INSERT INTO lancamentos (data, descricao, valor_centavos, comprovante) "
            "VALUES (?, ?, ?, ?)",
            (data_iso, descricao, centavos, nome),
        )
        self.con.commit()
        return cur.lastrowid

    def atualizar_campo(self, id_, campo, texto):
        if campo not in self.CAMPOS_EDITAVEIS:
            raise ValueError(f"Campo não editável: {campo}")
        coluna, validar = self.CAMPOS_EDITAVEIS[campo]
        novo = validar(texto)
        # 'coluna' vem da lista fixa acima, nunca do usuário.
        cur = self.con.execute(f"UPDATE lancamentos SET {coluna} = ? WHERE id = ?", (novo, id_))
        self.con.commit()
        if cur.rowcount == 0:
            raise ValueError("Lançamento não encontrado.")

    def anexar_comprovante(self, id_, origem):
        _validar_comprovante(origem)
        nome = self._copiar_comprovante(origem)
        cur = self.con.execute("UPDATE lancamentos SET comprovante = ? WHERE id = ?", (nome, id_))
        self.con.commit()
        if cur.rowcount == 0:
            raise ValueError("Lançamento não encontrado.")
        return nome

    def excluir(self, id_):
        """Remove o lançamento. O arquivo do comprovante é mantido na pasta."""
        self.con.execute("DELETE FROM lancamentos WHERE id = ?", (id_,))
        self.con.commit()

    def listar(self):
        linhas = self.con.execute(
            "SELECT id, data, descricao, valor_centavos, comprovante "
            "FROM lancamentos ORDER BY data, id"
        ).fetchall()
        return [
            {"id": i, "data": d, "descricao": desc, "valor": v, "comprovante": c}
            for i, d, desc, v, c in linhas
        ]

    def total_centavos(self):
        return self.con.execute("SELECT COALESCE(SUM(valor_centavos), 0) FROM lancamentos").fetchone()[0]

    def caminho_comprovante(self, nome):
        return os.path.join(self.pasta_comprovantes, nome)

    def fechar(self):
        self.con.close()

    def _copiar_comprovante(self, origem):
        nome = f"{uuid.uuid4().hex[:8]}_{os.path.basename(origem)}"
        shutil.copy2(origem, self.caminho_comprovante(nome))
        return nome


def _validar_descricao(texto):
    texto = texto.strip()
    if not texto:
        raise ValueError("A descrição não pode ficar vazia.")
    return texto


def _validar_comprovante(origem):
    if not origem:
        return
    if os.path.splitext(origem)[1].lower() not in EXTENSOES_COMPROVANTE:
        raise ValueError("Comprovante deve ser JPG, PNG ou PDF.")
    if not os.path.isfile(origem):
        raise ValueError("Arquivo do comprovante não encontrado.")
