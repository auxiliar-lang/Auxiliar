"""Planilha de lançamentos: data, descrição, valor e comprovante."""

import os
import sqlite3
import sys
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

import planilha as pl

TIPOS_ARQUIVO = [("Comprovantes", "*.jpg *.jpeg *.png *.pdf")]


def pasta_dados():
    """Pasta 'dados' ao lado do .exe (ou do app.py, ao rodar pelo Python)."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "dados")


class App(tk.Tk):
    COLUNAS = (
        ("data", "Data", 110),
        ("descricao", "Descrição", 380),
        ("valor", "Valor", 130),
        ("comprovante", "Comprovante", 220),
    )

    def __init__(self, planilha):
        super().__init__()
        self.title("Planilha de lançamentos")
        self.geometry("920x560")
        self.planilha = planilha
        self.comprovante_novo = None
        self.editor = None
        self._montar_formulario()
        self._montar_tabela()
        self._montar_rodape()
        self.recarregar()
        self.protocol("WM_DELETE_WINDOW", self._sair)

    # ---------- montagem da tela ----------
    def _montar_formulario(self):
        quadro = ttk.LabelFrame(self, text="Novo lançamento")
        quadro.pack(fill="x", padx=8, pady=8)

        self.var_data = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        self.var_desc = tk.StringVar()
        self.var_valor = tk.StringVar()
        self.var_anexo = tk.StringVar(value="(sem comprovante)")

        ttk.Label(quadro, text="Data").grid(row=0, column=0, padx=4, sticky="w")
        ttk.Label(quadro, text="Descrição").grid(row=0, column=1, padx=4, sticky="w")
        ttk.Label(quadro, text="Valor").grid(row=0, column=2, padx=4, sticky="w")

        entradas = (
            ttk.Entry(quadro, textvariable=self.var_data, width=12),
            ttk.Entry(quadro, textvariable=self.var_desc, width=40),
            ttk.Entry(quadro, textvariable=self.var_valor, width=14),
        )
        for coluna, entrada in enumerate(entradas):
            entrada.grid(row=1, column=coluna, padx=4, pady=2, sticky="we")
            entrada.bind("<Return>", lambda _e: self.adicionar())
        quadro.columnconfigure(1, weight=1)

        ttk.Button(quadro, text="Anexar comprovante…", command=self.escolher_anexo_novo).grid(
            row=1, column=3, padx=4
        )
        ttk.Label(quadro, textvariable=self.var_anexo, width=28).grid(row=1, column=4, padx=4)
        ttk.Button(quadro, text="Adicionar", command=self.adicionar).grid(row=1, column=5, padx=4)

    def _montar_tabela(self):
        quadro = ttk.Frame(self)
        quadro.pack(fill="both", expand=True, padx=8)

        ids = [c[0] for c in self.COLUNAS]
        self.tabela = ttk.Treeview(quadro, columns=ids, show="headings", selectmode="browse")
        for id_, titulo, largura in self.COLUNAS:
            self.tabela.heading(id_, text=titulo)
            self.tabela.column(id_, width=largura, anchor="e" if id_ == "valor" else "w")
        barra = ttk.Scrollbar(quadro, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        self.tabela.bind("<Double-1>", self._duplo_clique)
        self.tabela.bind("<Delete>", lambda _e: self.excluir())

    def _montar_rodape(self):
        quadro = ttk.Frame(self)
        quadro.pack(fill="x", padx=8, pady=8)
        ttk.Button(quadro, text="Abrir comprovante", command=self.abrir_comprovante).pack(side="left")
        ttk.Button(quadro, text="Trocar comprovante…", command=self.trocar_comprovante).pack(
            side="left", padx=4
        )
        ttk.Button(quadro, text="Excluir selecionado", command=self.excluir).pack(side="left")
        self.var_total = tk.StringVar()
        ttk.Label(quadro, textvariable=self.var_total, font=("Segoe UI", 11, "bold")).pack(side="right")
        ttk.Label(quadro, text="Dica: dê duplo clique numa célula para editar.").pack(
            side="right", padx=16
        )

    # ---------- dados ----------
    def recarregar(self):
        self._fechar_editor()
        self.tabela.delete(*self.tabela.get_children())
        for lin in self.planilha.listar():
            self.tabela.insert(
                "",
                "end",
                iid=str(lin["id"]),
                values=(
                    pl.formatar_data(lin["data"]),
                    lin["descricao"],
                    pl.formatar_valor(lin["valor"]),
                    pl.nome_exibicao_comprovante(lin["comprovante"]),
                ),
            )
        self.var_total.set("Total: " + pl.formatar_valor(self.planilha.total_centavos()))

    def escolher_anexo_novo(self):
        caminho = filedialog.askopenfilename(title="Escolha o comprovante", filetypes=TIPOS_ARQUIVO)
        if caminho:
            self.comprovante_novo = caminho
            self.var_anexo.set(os.path.basename(caminho))

    def adicionar(self):
        try:
            self.planilha.adicionar(
                self.var_data.get(), self.var_desc.get(), self.var_valor.get(), self.comprovante_novo
            )
        except (ValueError, OSError) as erro:
            messagebox.showwarning("Não foi possível adicionar", str(erro))
            return
        self.var_desc.set("")
        self.var_valor.set("")
        self.comprovante_novo = None
        self.var_anexo.set("(sem comprovante)")
        self.recarregar()

    def _id_selecionado(self):
        selecao = self.tabela.selection()
        if not selecao:
            messagebox.showinfo("Selecione uma linha", "Clique numa linha da tabela primeiro.")
            return None
        return int(selecao[0])

    def excluir(self):
        id_ = self._id_selecionado()
        if id_ is None:
            return
        if messagebox.askyesno(
            "Excluir lançamento",
            "Excluir o lançamento selecionado?\n(O arquivo do comprovante continua na pasta.)",
        ):
            self.planilha.excluir(id_)
            self.recarregar()

    def trocar_comprovante(self):
        id_ = self._id_selecionado()
        if id_ is None:
            return
        caminho = filedialog.askopenfilename(title="Escolha o comprovante", filetypes=TIPOS_ARQUIVO)
        if not caminho:
            return
        try:
            self.planilha.anexar_comprovante(id_, caminho)
        except (ValueError, OSError) as erro:
            messagebox.showwarning("Não foi possível anexar", str(erro))
            return
        self.recarregar()
        self.tabela.selection_set(str(id_))

    def abrir_comprovante(self, id_=None):
        if id_ is None:
            id_ = self._id_selecionado()
            if id_ is None:
                return
        lin = next((x for x in self.planilha.listar() if x["id"] == id_), None)
        if lin is None or not lin["comprovante"]:
            messagebox.showinfo("Sem comprovante", "Este lançamento não tem comprovante.")
            return
        caminho = self.planilha.caminho_comprovante(lin["comprovante"])
        if not os.path.isfile(caminho):
            messagebox.showwarning("Arquivo não encontrado", f"O arquivo não está mais em:\n{caminho}")
            return
        try:
            os.startfile(caminho)  # só existe no Windows
        except (AttributeError, OSError) as erro:
            messagebox.showwarning("Não foi possível abrir", str(erro))

    # ---------- edição direto na célula ----------
    def _duplo_clique(self, evento):
        if self.tabela.identify_region(evento.x, evento.y) != "cell":
            return
        iid = self.tabela.identify_row(evento.y)
        coluna = self.tabela.identify_column(evento.x)
        if not iid or not coluna:
            return
        campo = self.COLUNAS[int(coluna[1:]) - 1][0]
        if campo == "comprovante":
            self.abrir_comprovante(int(iid))
        else:
            self._editar_celula(iid, campo, coluna)

    def _editar_celula(self, iid, campo, coluna):
        self._fechar_editor()
        caixa = self.tabela.bbox(iid, coluna)
        if not caixa:
            return
        x, y, largura, altura = caixa
        texto = self.tabela.set(iid, campo)
        if campo == "valor":
            texto = pl.valor_para_edicao(self._centavos_da_linha(int(iid)))
        editor = ttk.Entry(self.tabela)
        editor.place(x=x, y=y, width=largura, height=altura)
        editor.insert(0, texto)
        editor.select_range(0, "end")
        editor.focus_set()
        editor.bind("<Return>", lambda _e: self._confirmar_edicao(iid, campo))
        editor.bind("<Escape>", lambda _e: self._fechar_editor())
        editor.bind("<FocusOut>", lambda _e: self._fechar_editor())
        self.editor = editor

    def _centavos_da_linha(self, id_):
        return next(x["valor"] for x in self.planilha.listar() if x["id"] == id_)

    def _confirmar_edicao(self, iid, campo):
        if self.editor is None:
            return
        texto = self.editor.get()
        self._fechar_editor()
        try:
            self.planilha.atualizar_campo(int(iid), campo, texto)
        except ValueError as erro:
            messagebox.showwarning("Valor não aceito", str(erro))
            return
        self.recarregar()
        self.tabela.selection_set(iid)

    def _fechar_editor(self):
        if self.editor is not None:
            editor, self.editor = self.editor, None
            editor.unbind("<FocusOut>")
            editor.destroy()

    def _sair(self):
        self.planilha.fechar()
        self.destroy()


def main():
    pasta = pasta_dados()
    try:
        planilha = pl.Planilha(pasta)
    except (OSError, sqlite3.Error) as erro:
        # Ex.: programa colocado numa pasta sem permissão de escrita.
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Não foi possível abrir os dados",
            f"Não consegui criar/abrir a pasta de dados:\n{pasta}\n\n{erro}\n\n"
            "Mova o programa para uma pasta onde você pode salvar arquivos (ex.: Documentos).",
        )
        return
    App(planilha).mainloop()


if __name__ == "__main__":
    main()
