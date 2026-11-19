/**
 * wa.db — tudo que a ponte vê do WhatsApp, em SQLite.
 * O leitor em Python é core/src/jarvis_core/ingest/whatsapp_bridge.py: mudou aqui, muda lá.
 */
import Database from "better-sqlite3";
import { chmodSync, mkdirSync } from "node:fs";
import { join } from "node:path";

export interface MensagemLinha {
  id: string;
  jid: string;
  autor_jid: string;
  de_mim: number;
  tipo: string;
  texto: string;
  menciona_me: number;
  enviada_em: number; // unix, segundos
}

const ESQUEMA = `
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE IF NOT EXISTS chats (
  jid TEXT PRIMARY KEY, nome TEXT, eh_grupo INTEGER NOT NULL DEFAULT 0,
  atualizado_em INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS contatos (jid TEXT PRIMARY KEY, nome TEXT);
CREATE TABLE IF NOT EXISTS lid_pn (lid TEXT PRIMARY KEY, pn TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS mensagens (
  id TEXT NOT NULL, jid TEXT NOT NULL, autor_jid TEXT NOT NULL, de_mim INTEGER NOT NULL,
  tipo TEXT NOT NULL, texto TEXT NOT NULL, menciona_me INTEGER NOT NULL DEFAULT 0,
  enviada_em INTEGER NOT NULL, PRIMARY KEY (jid, id)
);
CREATE INDEX IF NOT EXISTS mensagens_por_chat ON mensagens (jid, enviada_em);
`;

export class Store {
  private db: Database.Database;
  private stmtMsg: Database.Statement;
  private stmtChat: Database.Statement;
  private stmtToque: Database.Statement;
  private stmtContato: Database.Statement;

  constructor(dataDir: string) {
    mkdirSync(dataDir, { recursive: true, mode: 0o700 });
    chmodSync(dataDir, 0o700);
    const caminho = join(dataDir, "wa.db");
    this.db = new Database(caminho);
    chmodSync(caminho, 0o600);
    this.db.exec(ESQUEMA);
    this.stmtMsg = this.db.prepare(
      `INSERT INTO mensagens VALUES (@id, @jid, @autor_jid, @de_mim, @tipo, @texto, @menciona_me, @enviada_em)
       ON CONFLICT (jid, id) DO UPDATE SET texto = excluded.texto, tipo = excluded.tipo`,
    );
    this.stmtChat = this.db.prepare(
      `INSERT INTO chats (jid, nome, eh_grupo, atualizado_em) VALUES (@jid, @nome, @eh_grupo, @atualizado_em)
       ON CONFLICT (jid) DO UPDATE SET
         nome = COALESCE(excluded.nome, chats.nome),
         atualizado_em = MAX(chats.atualizado_em, excluded.atualizado_em)`,
    );
    this.stmtToque = this.db.prepare(
      `INSERT INTO chats (jid, eh_grupo, atualizado_em) VALUES (?, ?, ?)
       ON CONFLICT (jid) DO UPDATE SET atualizado_em = MAX(chats.atualizado_em, excluded.atualizado_em)`,
    );
    this.stmtContato = this.db.prepare(
      `INSERT INTO contatos VALUES (?, ?) ON CONFLICT (jid) DO UPDATE SET nome = COALESCE(excluded.nome, contatos.nome)`,
    );
  }

  setMeta(chave: string, valor: string): void {
    this.db.prepare("INSERT OR REPLACE INTO meta VALUES (?, ?)").run(chave, valor);
  }

  salvarMensagens(linhas: MensagemLinha[], ehGrupo: (jid: string) => boolean): void {
    const tx = this.db.transaction((ls: MensagemLinha[]) => {
      for (const l of ls) {
        this.stmtMsg.run(l);
        this.stmtToque.run(l.jid, ehGrupo(l.jid) ? 1 : 0, l.enviada_em);
      }
    });
    tx(linhas);
  }

  salvarChat(jid: string, nome: string | null, ehGrupo: boolean, atualizadoEm: number): void {
    this.stmtChat.run({ jid, nome, eh_grupo: ehGrupo ? 1 : 0, atualizado_em: atualizadoEm });
  }

  salvarContato(jid: string, nome: string | null): void {
    this.stmtContato.run(jid, nome);
  }

  salvarLidPn(lid: string, pn: string): void {
    this.db.prepare("INSERT OR REPLACE INTO lid_pn VALUES (?, ?)").run(lid, pn);
  }

  fechar(): void {
    this.db.close();
  }
}
