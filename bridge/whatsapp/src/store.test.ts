import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";
import { Store, type MensagemLinha } from "./store.js";

const ANA = "5511988887777@s.whatsapp.net";
const GRUPO = "120363000000000000@g.us";
const linha = (id: string, jid: string, t: number, texto = "oi"): MensagemLinha => ({
  id, jid, autor_jid: ANA, de_mim: 0, tipo: "texto", texto, menciona_me: 0, enviada_em: t,
});

test("cria a pasta e o banco só para o dono", () => {
  const dir = join(mkdtempSync(join(tmpdir(), "wa-")), "dados");
  new Store(dir).fechar();
  assert.equal(statSync(dir).mode & 0o777, 0o700);
  assert.equal(statSync(join(dir, "wa.db")).mode & 0o777, 0o600);
});

test("grava mensagens, atualiza a conversa e não volta no tempo", () => {
  const dir = mkdtempSync(join(tmpdir(), "wa-"));
  const s = new Store(dir);
  s.setMeta("meu_jid", "eu@s.whatsapp.net");
  s.salvarChat(GRUPO, "PI VI", true, 0);
  s.salvarMensagens([linha("a", ANA, 200), linha("b", GRUPO, 100)], (j) => j === GRUPO);
  s.salvarMensagens([linha("a", ANA, 150, "editada")], () => false); // mais antiga: não regride
  s.salvarChat(ANA, null, false, 50); // nome nulo não apaga, data antiga não regride
  s.salvarContato(ANA, "Ana");
  s.salvarContato(ANA, null);
  s.salvarLidPn("123@lid", ANA);
  s.fechar();

  const db = new Database(join(dir, "wa.db"), { readonly: true });
  const chats = db.prepare("SELECT jid, nome, eh_grupo, atualizado_em FROM chats ORDER BY jid").all();
  assert.deepEqual(chats, [
    { jid: GRUPO, nome: "PI VI", eh_grupo: 1, atualizado_em: 100 },
    { jid: ANA, nome: null, eh_grupo: 0, atualizado_em: 200 },
  ]);
  const msg = db.prepare("SELECT texto FROM mensagens WHERE id = 'a'").get() as { texto: string };
  assert.equal(msg.texto, "editada");
  assert.deepEqual(db.prepare("SELECT nome FROM contatos").get(), { nome: "Ana" });
  assert.deepEqual(db.prepare("SELECT pn FROM lid_pn").get(), { pn: ANA });
  assert.deepEqual(db.prepare("SELECT valor FROM meta").get(), { valor: "eu@s.whatsapp.net" });
  db.close();
});
