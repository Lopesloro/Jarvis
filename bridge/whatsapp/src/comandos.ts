/** Comandos recebidos pelo stdin. Separado do index.ts para a trava de envio ser testável. */

export interface Ambiente {
  podeEnviar: boolean;
  enviar: ((jid: string, texto: string) => Promise<unknown>) | null; // null = sem conexão
  emitir: (evento: Record<string, unknown>) => void;
  encerrar: (codigo: number) => void;
}

export async function tratarComando(linha: string, amb: Ambiente): Promise<void> {
  let cmd: { type?: string; jid?: string; text?: string };
  try {
    cmd = JSON.parse(linha);
  } catch {
    return amb.emitir({ type: "error", message: "JSON inválido no stdin" });
  }
  if (cmd.type === "send") {
    if (!amb.podeEnviar) {
      return amb.emitir({
        type: "error",
        message: "Envio desligado (modo só leitura). Defina JARVIS_WA_ALLOW_SEND=1.",
      });
    }
    if (!amb.enviar || !cmd.jid || !cmd.text) {
      return amb.emitir({ type: "error", message: "send exige jid e text" });
    }
    try {
      await amb.enviar(cmd.jid, cmd.text);
    } catch (e) {
      amb.emitir({ type: "error", message: `Falha no envio: ${(e as Error).message}` });
    }
  } else if (cmd.type === "disconnect") {
    amb.encerrar(0);
  }
}
