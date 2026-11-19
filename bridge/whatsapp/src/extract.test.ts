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
