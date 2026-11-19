/** Converte mensagens do Baileys em linhas do wa.db. Funções puras, testadas em extract.test.ts. */
import {
  isJidGroup,
  normalizeMessageContent,
  type WAMessage,
} from "@whiskeysockets/baileys";
import type { MensagemLinha } from "./store.js";

export interface Eu {
  jid: string; // 55199...@s.whatsapp.net
  lid?: string; // ...@lid
}

const IGNORAR = new Set(["status@broadcast"]);

function semDispositivo(jid: string): string {
  // "5519...:12@s.whatsapp.net" → "5519...@s.whatsapp.net"
  return jid.replace(/:\d+@/, "@");
}

export function souEu(jid: string | null | undefined, eu: Eu): boolean {
  if (!jid) return false;
  const j = semDispositivo(jid);
  return j === semDispositivo(eu.jid) || (!!eu.lid && j === semDispositivo(eu.lid));
}

/** Tipo e texto legível. Mídia sem legenda vira marcador; áudio é transcrito depois (F1). */
export function conteudo(msg: WAMessage): { tipo: string; texto: string } | null {
  const c = normalizeMessageContent(msg.message);
  if (!c) return null;
  if (c.conversation) return { tipo: "texto", texto: c.conversation };
  if (c.extendedTextMessage?.text) return { tipo: "texto", texto: c.extendedTextMessage.text };
  if (c.imageMessage) return { tipo: "imagem", texto: c.imageMessage.caption || "[imagem]" };
  if (c.videoMessage) return { tipo: "video", texto: c.videoMessage.caption || "[vídeo]" };
  if (c.audioMessage) return { tipo: "audio", texto: c.audioMessage.ptt ? "[áudio de voz]" : "[áudio]" };
  if (c.documentMessage) {
    const d = c.documentMessage;
    return { tipo: "documento", texto: d.caption || `[documento] ${d.fileName ?? ""}`.trim() };
  }
  if (c.contactMessage) return { tipo: "contato", texto: `[contato] ${c.contactMessage.displayName ?? ""}`.trim() };
  if (c.locationMessage) return { tipo: "localizacao", texto: "[localização]" };
  if (c.pollCreationMessage || c.pollCreationMessageV3) {
    const p = c.pollCreationMessage ?? c.pollCreationMessageV3;
    return { tipo: "enquete", texto: `[enquete] ${p?.name ?? ""}`.trim() };
  }
  return null; // reações, edições, mensagens de protocolo
}

function contexto(msg: WAMessage) {
  const c = normalizeMessageContent(msg.message);
  return (
    c?.extendedTextMessage?.contextInfo ??
    c?.imageMessage?.contextInfo ??
    c?.videoMessage?.contextInfo ??
    c?.documentMessage?.contextInfo ??
    c?.audioMessage?.contextInfo ??
    undefined
  );
}

/** Menção direta (@você) ou resposta a uma mensagem sua. */
export function mencionaMe(msg: WAMessage, eu: Eu): boolean {
  const ctx = contexto(msg);
  if (!ctx) return false;
  if ((ctx.mentionedJid ?? []).some((j) => souEu(j, eu))) return true;
  return souEu(ctx.participant, eu);
}

function segundos(ts: WAMessage["messageTimestamp"]): number {
  if (ts == null) return Math.floor(Date.now() / 1000);
  return typeof ts === "number" ? ts : Number(ts.toString());
}

export function paraLinha(msg: WAMessage, eu: Eu): MensagemLinha | null {
  const jid = msg.key.remoteJid;
  if (!jid || IGNORAR.has(jid) || jid.endsWith("@newsletter") || !msg.key.id) return null;
  const c = conteudo(msg);
  if (!c) return null;
  const deMim = !!msg.key.fromMe;
  const autor = deMim ? eu.jid : (msg.key.participant ?? jid);
  return {
    id: msg.key.id,
    jid,
    autor_jid: semDispositivo(autor),
    de_mim: deMim ? 1 : 0,
    tipo: c.tipo,
    texto: c.texto,
    menciona_me: !deMim && isJidGroup(jid) && mencionaMe(msg, eu) ? 1 : 0,
    enviada_em: segundos(msg.messageTimestamp),
  };
}
