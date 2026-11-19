import { test } from "node:test";
import assert from "node:assert/strict";
import type { WAMessage } from "@whiskeysockets/baileys";
import { paraLinha, souEu, type Eu } from "./extract.js";

const EU: Eu = { jid: "5519999990000@s.whatsapp.net", lid: "111222333@lid" };
const GRUPO = "120363000000000000@g.us";

const msg = (m: Partial<WAMessage>): WAMessage =>
  ({ key: { id: "ID1", remoteJid: "5511988887777@s.whatsapp.net", fromMe: false }, messageTimestamp: 1_700_000_000, ...m }) as WAMessage;

test("texto simples de conversa direta", () => {
  const l = paraLinha(msg({ message: { conversation: "Oi!" } }), EU);
  assert.equal(l?.texto, "Oi!");
  assert.equal(l?.de_mim, 0);
  assert.equal(l?.autor_jid, "5511988887777@s.whatsapp.net");
});

test("mensagem minha usa meu jid como autor", () => {
  const l = paraLinha(msg({ key: { id: "ID2", remoteJid: "5511988887777@s.whatsapp.net", fromMe: true }, message: { conversation: "Tudo bem" } }), EU);
  assert.equal(l?.de_mim, 1);
  assert.equal(l?.autor_jid, EU.jid);
});

test("legenda de imagem e áudio de voz viram texto legível", () => {
  assert.equal(paraLinha(msg({ message: { imageMessage: { caption: "comprovante" } } }), EU)?.texto, "comprovante");
  assert.equal(paraLinha(msg({ message: { audioMessage: { ptt: true } } }), EU)?.tipo, "audio");
});

test("menção por LID em grupo e resposta a mim contam como menção", () => {
  const mencao = msg({
    key: { id: "ID3", remoteJid: GRUPO, participant: "5511988887777:3@s.whatsapp.net", fromMe: false },
    message: { extendedTextMessage: { text: "@Gabriel olha isso", contextInfo: { mentionedJid: [EU.lid!] } } },
  });
  const l = paraLinha(mencao, EU);
  assert.equal(l?.menciona_me, 1);
  assert.equal(l?.autor_jid, "5511988887777@s.whatsapp.net"); // sem o :3 do dispositivo

  const resposta = msg({
    key: { id: "ID4", remoteJid: GRUPO, participant: "5511988887777@s.whatsapp.net", fromMe: false },
    message: { extendedTextMessage: { text: "concordo", contextInfo: { participant: EU.jid } } },
  });
  assert.equal(paraLinha(resposta, EU)?.menciona_me, 1);
});

test("status, reações e mensagens vazias são ignorados", () => {
  assert.equal(paraLinha(msg({ key: { id: "S", remoteJid: "status@broadcast" }, message: { conversation: "x" } }), EU), null);
  assert.equal(paraLinha(msg({ message: { reactionMessage: { text: "👍" } } }), EU), null);
  assert.equal(paraLinha(msg({ message: undefined }), EU), null);
});

test("souEu ignora o sufixo de dispositivo", () => {
  assert.ok(souEu("5519999990000:12@s.whatsapp.net", EU));
  assert.ok(!souEu("5511988887777@s.whatsapp.net", EU));
});

test("todos os tipos de conteúdo viram texto legível", async () => {
  const { conteudo } = await import("./extract.js");
  const casos: [WAMessage["message"], string, string][] = [
    [{ extendedTextMessage: { text: "longo" } }, "texto", "longo"],
    [{ imageMessage: {} }, "imagem", "[imagem]"],
    [{ videoMessage: { caption: "olha" } }, "video", "olha"],
    [{ videoMessage: {} }, "video", "[vídeo]"],
    [{ audioMessage: { ptt: false } }, "audio", "[áudio]"],
    [{ audioMessage: { ptt: true } }, "audio", "[áudio de voz]"],
    [{ documentMessage: { caption: "segue" } }, "documento", "segue"],
    [{ documentMessage: { fileName: "cv.pdf" } }, "documento", "[documento] cv.pdf"],
    [{ documentMessage: {} }, "documento", "[documento]"],
    [{ contactMessage: { displayName: "Ana" } }, "contato", "[contato] Ana"],
    [{ contactMessage: {} }, "contato", "[contato]"],
    [{ locationMessage: {} }, "localizacao", "[localização]"],
    [{ pollCreationMessage: { name: "Data da prova?" } }, "enquete", "[enquete] Data da prova?"],
    [{ pollCreationMessageV3: {} }, "enquete", "[enquete]"],
    [{ ephemeralMessage: { message: { conversation: "temporária" } } }, "texto", "temporária"],
  ];
  for (const [message, tipo, texto] of casos) {
    assert.deepEqual(conteudo(msg({ message })), { tipo, texto }, JSON.stringify(message));
  }
});

test("menção ou resposta dentro de mídia também conta", () => {
  const base = { key: { id: "M", remoteJid: GRUPO, participant: "5511988887777@s.whatsapp.net", fromMe: false } };
  const ctx = { mentionedJid: [EU.jid] };
  for (const message of [
    { imageMessage: { contextInfo: ctx } },
    { videoMessage: { contextInfo: ctx } },
    { documentMessage: { contextInfo: ctx } },
    { audioMessage: { contextInfo: { participant: EU.jid } } },
  ]) {
    assert.equal(paraLinha(msg({ ...base, message }), EU)?.menciona_me, 1, JSON.stringify(message));
  }
  assert.equal(paraLinha(msg({ ...base, message: { conversation: "sem contexto" } }), EU)?.menciona_me, 0);
  assert.equal(
    paraLinha(msg({ ...base, message: { extendedTextMessage: { text: "x", contextInfo: {} } } }), EU)?.menciona_me,
    0,
  );
});

test("minha mensagem em grupo não conta como menção e autor em conversa direta é o jid", () => {
  const minha = msg({
    key: { id: "N", remoteJid: GRUPO, fromMe: true },
    message: { extendedTextMessage: { text: "@eu", contextInfo: { mentionedJid: [EU.jid] } } },
  });
  assert.equal(paraLinha(minha, EU)?.menciona_me, 0);
});

test("carimbo de tempo: número, Long e ausente", () => {
  assert.equal(paraLinha(msg({ message: { conversation: "a" }, messageTimestamp: 1_700_000_000 }), EU)?.enviada_em, 1_700_000_000);
  const longo = { toString: () => "1700000001" } as unknown as WAMessage["messageTimestamp"];
  assert.equal(paraLinha(msg({ message: { conversation: "a" }, messageTimestamp: longo }), EU)?.enviada_em, 1_700_000_001);
  const agora = Math.floor(Date.now() / 1000);
  const sem = paraLinha(msg({ message: { conversation: "a" }, messageTimestamp: null }), EU)!.enviada_em;
  assert.ok(Math.abs(sem - agora) <= 1);
});

test("canais (newsletter), mensagem sem id ou sem conversa são ignorados", () => {
  assert.equal(paraLinha(msg({ key: { id: "C", remoteJid: "123@newsletter" }, message: { conversation: "x" } }), EU), null);
  assert.equal(paraLinha(msg({ key: { remoteJid: "5511@s.whatsapp.net" }, message: { conversation: "x" } }), EU), null);
  assert.equal(paraLinha(msg({ key: { id: "D" }, message: { conversation: "x" } }), EU), null);
});

test("souEu sem LID e com jid vazio", () => {
  const semLid: Eu = { jid: EU.jid };
  assert.ok(!souEu("111222333@lid", semLid));
  assert.ok(!souEu(undefined, semLid));
  assert.ok(!souEu("", semLid));
});
