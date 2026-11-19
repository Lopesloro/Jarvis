import { test } from "node:test";
import assert from "node:assert/strict";
import { tratarComando, type Ambiente } from "./comandos.js";

function ambiente(over: Partial<Ambiente> = {}) {
  const eventos: Record<string, unknown>[] = [];
  const enviados: [string, string][] = [];
  const saidas: number[] = [];
  const amb: Ambiente = {
    podeEnviar: false,
    enviar: async (jid, texto) => void enviados.push([jid, texto]),
    emitir: (e) => void eventos.push(e),
    encerrar: (c) => void saidas.push(c),
    ...over,
  };
  return { amb, eventos, enviados, saidas };
}

test("modo só leitura: send é recusado e nada é enviado", async () => {
  const { amb, eventos, enviados } = ambiente();
  await tratarComando(JSON.stringify({ type: "send", jid: "x@s.whatsapp.net", text: "oi" }), amb);
  assert.deepEqual(enviados, []);
  assert.match(String(eventos[0].message), /só leitura/);
});

test("com envio liberado: exige jid, texto e conexão", async () => {
  const { amb, eventos, enviados } = ambiente({ podeEnviar: true });
  await tratarComando(JSON.stringify({ type: "send", jid: "x" }), amb);
  await tratarComando(JSON.stringify({ type: "send", text: "oi" }), amb);
  await tratarComando(JSON.stringify({ type: "send", jid: "x", text: "oi" }), { ...amb, enviar: null });
  assert.equal(eventos.length, 3);
  assert.deepEqual(enviados, []);
  await tratarComando(JSON.stringify({ type: "send", jid: "x", text: "oi" }), amb);
  assert.deepEqual(enviados, [["x", "oi"]]);
});

test("falha no envio vira evento de erro", async () => {
  const { amb, eventos } = ambiente({
    podeEnviar: true,
    enviar: async () => {
      throw new Error("offline");
    },
  });
  await tratarComando(JSON.stringify({ type: "send", jid: "x", text: "oi" }), amb);
  assert.equal(eventos[0].message, "Falha no envio: offline");
});

test("JSON inválido, disconnect e comando desconhecido", async () => {
  const { amb, eventos, saidas } = ambiente();
  await tratarComando("{nao", amb);
  await tratarComando(JSON.stringify({ type: "disconnect" }), amb);
  await tratarComando(JSON.stringify({ type: "outro" }), amb);
  assert.equal(eventos[0].message, "JSON inválido no stdin");
  assert.deepEqual(saidas, [0]);
  assert.equal(eventos.length, 1);
});
