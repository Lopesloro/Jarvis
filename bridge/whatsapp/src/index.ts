/**
 * Ponte WhatsApp do Jarvis.
 *
 * Diferenças para a ponte do OpenJarvis (channels/whatsapp_baileys_bridge):
 *  - sincroniza o HISTÓRICO completo (syncFullHistory) e grava tudo em <data-dir>/wa.db;
 *  - guarda também as SUAS mensagens (para saber se você já respondeu);
 *  - entende legenda, áudio, documento, enquete, menções e respostas a você;
 *  - SÓ LEITURA por padrão: o comando "send" é recusado sem JARVIS_WA_ALLOW_SEND=1;
 *  - não marca presença online nem envia confirmação de leitura.
 *
 * Saída em stdout (uma linha JSON por evento), compatível com o protocolo do OpenJarvis:
 *   {"type":"qr","data":...} {"type":"status","status":"connected"|"disconnected"}
 *   {"type":"message","jid":...,"sender":...,"text":...,"message_id":...}
 *   {"type":"history","progress":..,"messages":..} {"type":"error","message":...}
 */
import makeWASocket, {
  Browsers,
  DisconnectReason,
  isJidGroup,
  jidNormalizedUser,
  useMultiFileAuthState,
  type WASocket,
} from "@whiskeysockets/baileys";
import pino from "pino";
import qrcode from "qrcode-terminal";
import { join } from "node:path";
import { homedir } from "node:os";
import * as readline from "node:readline";
import { paraLinha, type Eu } from "./extract.js";
import { Store } from "./store.js";

const PODE_ENVIAR = process.env.JARVIS_WA_ALLOW_SEND === "1";

function emitir(evento: Record<string, unknown>): void {
  process.stdout.write(JSON.stringify(evento) + "\n");
}

function argumento(nome: string, padrao: string): string {
  const i = process.argv.indexOf(nome);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : padrao;
}

const dataDir = argumento("--data-dir", join(homedir(), ".jarvis", "whatsapp"));
const store = new Store(dataDir);
const log = pino({ level: process.env.JARVIS_WA_LOG ?? "warn" }, pino.destination(2));
let sock: WASocket | null = null;
let eu: Eu = { jid: "" };
let tentativas = 0;

async function iniciar(): Promise<void> {
  const { state, saveCreds } = await useMultiFileAuthState(join(dataDir, "auth"));
  sock = makeWASocket({
    auth: state,
    logger: log,
    browser: Browsers.macOS("Desktop"), // necessário para receber o histórico completo
    syncFullHistory: true,
    markOnlineOnConnect: false, // o celular continua recebendo notificações
    generateHighQualityLinkPreview: false,
  });
  const s = sock;

  s.ev.on("creds.update", saveCreds);

  s.ev.on("connection.update", async ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      qrcode.generate(qr, { small: true }, (code) => process.stderr.write(code + "\n"));
      emitir({ type: "qr", data: qr });
    }
    if (connection === "open") {
      tentativas = 0;
      eu = { jid: jidNormalizedUser(s.user?.id), lid: s.user?.lid ? jidNormalizedUser(s.user.lid) : undefined };
      store.setMeta("meu_jid", eu.jid);
      if (eu.lid) store.setMeta("meu_lid", eu.lid);
      emitir({ type: "status", status: "connected" });
      try {
        const grupos = await s.groupFetchAllParticipating();
        for (const g of Object.values(grupos)) store.salvarChat(g.id, g.subject ?? null, true, 0);
      } catch (e) {
        log.warn({ e }, "falha ao listar grupos");
      }
    }
    if (connection === "close") {
      emitir({ type: "status", status: "disconnected" });
      const codigo = (lastDisconnect?.error as { output?: { statusCode?: number } } | undefined)?.output
        ?.statusCode;
      if (codigo === DisconnectReason.loggedOut) {
        emitir({ type: "error", message: "Sessão encerrada no celular. Apague <data-dir>/auth e pareie de novo." });
        process.exit(2);
      }
      // backoff exponencial até 5 min para não martelar o servidor do WhatsApp
      const espera = Math.min(300_000, 2_000 * 2 ** tentativas++);
      setTimeout(() => void iniciar(), espera);
    }
  });

  s.ev.on("messaging-history.set", ({ chats, contacts, messages, lidPnMappings, progress }) => {
    for (const c of contacts) store.salvarContato(c.phoneNumber ?? c.id, c.name ?? c.notify ?? null);
    for (const m of lidPnMappings ?? []) store.salvarLidPn(m.lid, m.pn);
    for (const c of chats) {
      if (!c.id) continue;
      const ts = c.conversationTimestamp ? Number(c.conversationTimestamp.toString()) : 0;
      store.salvarChat(c.id, c.name ?? null, !!isJidGroup(c.id), ts);
    }
    const linhas = messages.map((m) => paraLinha(m, eu)).filter((l) => l !== null);
    store.salvarMensagens(linhas, (j) => !!isJidGroup(j));
    emitir({ type: "history", progress: progress ?? null, messages: linhas.length });
  });

  s.ev.on("contacts.upsert", (cs) => cs.forEach((c) => store.salvarContato(c.phoneNumber ?? c.id, c.name ?? c.notify ?? null)));
  s.ev.on("contacts.update", (cs) =>
    cs.forEach((c) => c.id && store.salvarContato(c.id, c.name ?? c.notify ?? null)),
  );
  s.ev.on("chats.upsert", (cs) =>
    cs.forEach((c) => c.id && store.salvarChat(c.id, c.name ?? null, !!isJidGroup(c.id), 0)),
  );
  s.ev.on("groups.update", (gs) => gs.forEach((g) => g.id && g.subject && store.salvarChat(g.id, g.subject, true, 0)));

  s.ev.on("messages.upsert", ({ messages }) => {
    const linhas = messages.map((m) => paraLinha(m, eu)).filter((l) => l !== null);
    store.salvarMensagens(linhas, (j) => !!isJidGroup(j));
    for (const l of linhas) {
      if (l.de_mim) continue;
      emitir({ type: "message", jid: l.jid, sender: l.autor_jid, text: l.texto, message_id: l.id });
    }
  });
}

readline.createInterface({ input: process.stdin }).on("line", async (linha) => {
  let cmd: { type?: string; jid?: string; text?: string };
  try {
    cmd = JSON.parse(linha);
  } catch {
    return emitir({ type: "error", message: "JSON inválido no stdin" });
  }
  if (cmd.type === "send") {
    if (!PODE_ENVIAR) {
      return emitir({ type: "error", message: "Envio desligado (modo só leitura). Defina JARVIS_WA_ALLOW_SEND=1." });
    }
    if (!sock || !cmd.jid || !cmd.text) return emitir({ type: "error", message: "send exige jid e text" });
    try {
      await sock.sendMessage(cmd.jid, { text: cmd.text });
    } catch (e) {
      emitir({ type: "error", message: `Falha no envio: ${(e as Error).message}` });
    }
  } else if (cmd.type === "disconnect") {
    encerrar(0);
  }
});

function encerrar(codigo: number): never {
  sock?.end(undefined);
  store.fechar();
  process.exit(codigo);
}
process.on("SIGTERM", () => encerrar(0));
process.on("SIGINT", () => encerrar(0));

iniciar().catch((e) => {
  emitir({ type: "error", message: `Fatal: ${(e as Error).message}` });
  process.exit(1);
});
