import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import planilha as pl


class TestParse(unittest.TestCase):
    def test_data_valida(self):
        self.assertEqual(pl.parse_data("05/11/2026"), "2026-11-05")

    def test_data_invalida(self):
        for texto in ("31/02/2026", "abc", "", "2026-11-05"):
            with self.assertRaises(ValueError):
                pl.parse_data(texto)

    def test_valor_valido(self):
        casos = {"1.234,56": 123456, "12,5": 1250, "R$ 10": 1000, "10.5": 1050, "-3,00": -300}
        for texto, esperado in casos.items():
            self.assertEqual(pl.parse_valor(texto), esperado, texto)

    def test_valor_invalido(self):
        for texto in ("abc", "", "1,234", "1,2,3", "NaN", "Infinity"):
            with self.assertRaises(ValueError, msg=texto):
                pl.parse_valor(texto)

    def test_formatar(self):
        self.assertEqual(pl.formatar_valor(123456), "R$ 1.234,56")
        self.assertEqual(pl.formatar_valor(0), "R$ 0,00")
        self.assertEqual(pl.formatar_valor(-500), "-R$ 5,00")
        self.assertEqual(pl.valor_para_edicao(123456), "1234,56")
        self.assertEqual(pl.formatar_data("2026-11-05"), "05/11/2026")


class TestPlanilha(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dados = os.path.join(self.tmp.name, "dados")
        self.p = pl.Planilha(self.dados)
        self.addCleanup(self.p.fechar)

    def _arquivo(self, nome, conteudo=b"x"):
        caminho = os.path.join(self.tmp.name, nome)
        with open(caminho, "wb") as f:
            f.write(conteudo)
        return caminho

    def test_adicionar_e_listar_ordenado_por_data(self):
        self.p.adicionar("06/11/2026", "B", "20,00")
        self.p.adicionar("05/11/2026", "A", "10,50")
        linhas = self.p.listar()
        self.assertEqual([x["descricao"] for x in linhas], ["A", "B"])
        self.assertEqual(self.p.total_centavos(), 3050)

    def test_adicionar_com_comprovante_copia_arquivo(self):
        origem = self._arquivo("nota.pdf", b"pdf")
        id_ = self.p.adicionar("05/11/2026", "Café", "5,00", origem)
        nome = self.p.listar()[0]["comprovante"]
        self.assertTrue(os.path.isfile(self.p.caminho_comprovante(nome)))
        self.assertEqual(pl.nome_exibicao_comprovante(nome), "nota.pdf")
        self.assertIsInstance(id_, int)

    def test_mesmo_nome_de_arquivo_nao_sobrescreve(self):
        a = self._arquivo("foto.jpg", b"1")
        self.p.adicionar("05/11/2026", "um", "1,00", a)
        self.p.adicionar("05/11/2026", "dois", "1,00", a)
        nomes = {x["comprovante"] for x in self.p.listar()}
        self.assertEqual(len(nomes), 2)

    def test_extensao_invalida_rejeitada(self):
        origem = self._arquivo("nota.txt")
        with self.assertRaises(ValueError):
            self.p.adicionar("05/11/2026", "x", "1,00", origem)
        self.assertEqual(self.p.listar(), [])

    def test_comprovante_inexistente(self):
        with self.assertRaises(ValueError):
            self.p.adicionar("05/11/2026", "x", "1,00", os.path.join(self.tmp.name, "nao.pdf"))

    def test_entrada_invalida_nao_deixa_copia_orfa(self):
        origem = self._arquivo("nota.png")
        with self.assertRaises(ValueError):
            self.p.adicionar("05/11/2026", "x", "abc", origem)
        self.assertEqual(os.listdir(self.p.pasta_comprovantes), [])

    def test_descricao_vazia(self):
        with self.assertRaises(ValueError):
            self.p.adicionar("05/11/2026", "   ", "1,00")

    def test_atualizar_campos(self):
        id_ = self.p.adicionar("05/11/2026", "A", "1,00")
        self.p.atualizar_campo(id_, "descricao", " Nova ")
        self.p.atualizar_campo(id_, "valor", "2,50")
        self.p.atualizar_campo(id_, "data", "07/11/2026")
        lin = self.p.listar()[0]
        self.assertEqual((lin["descricao"], lin["valor"], lin["data"]), ("Nova", 250, "2026-11-07"))

    def test_atualizar_invalido_mantem_valor(self):
        id_ = self.p.adicionar("05/11/2026", "A", "1,00")
        with self.assertRaises(ValueError):
            self.p.atualizar_campo(id_, "valor", "abc")
        with self.assertRaises(ValueError):
            self.p.atualizar_campo(id_, "comprovante", "x")
        self.assertEqual(self.p.listar()[0]["valor"], 100)

    def test_atualizar_id_inexistente(self):
        with self.assertRaises(ValueError):
            self.p.atualizar_campo(999, "descricao", "x")

    def test_trocar_comprovante(self):
        id_ = self.p.adicionar("05/11/2026", "A", "1,00")
        self.p.anexar_comprovante(id_, self._arquivo("a.jpeg"))
        self.assertTrue(self.p.listar()[0]["comprovante"].endswith("a.jpeg"))

    def test_excluir_mantem_arquivo(self):
        origem = self._arquivo("n.pdf")
        id_ = self.p.adicionar("05/11/2026", "A", "1,00", origem)
        nome = self.p.listar()[0]["comprovante"]
        self.p.excluir(id_)
        self.assertEqual(self.p.listar(), [])
        self.assertTrue(os.path.isfile(self.p.caminho_comprovante(nome)))

    def test_dados_persistem_ao_reabrir(self):
        self.p.adicionar("05/11/2026", "A", "1,00")
        self.p.fechar()
        outra = pl.Planilha(self.dados)
        self.addCleanup(outra.fechar)
        self.assertEqual(len(outra.listar()), 1)
        self.p = outra


if __name__ == "__main__":
    unittest.main()
