#!/bin/zsh
# Instala o Jarvis para subir sozinho a cada login, sem custo por token (modelo local).
# Idempotente: pode rodar de novo depois de atualizar o código.
set -eu
RAIZ="$HOME/jarvis"
J="$HOME/.jarvis"
LA="$HOME/Library/LaunchAgents"
UID_ATUAL=$(id -u)

echo "→ pastas"
mkdir -p "$J/logs" "$J/whatsapp" "$LA" "$HOME/.local/bin"
chmod 700 "$J" "$J/whatsapp"

echo "→ configuração"
[ -f "$J/jarvis.toml" ] || cp "$RAIZ/config/jarvis.example.toml" "$J/jarvis.toml"
chmod 600 "$J/jarvis.toml"
if [ ! -f "$J/env" ]; then
  umask 077
  print "JARVIS_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" > "$J/env"
  print "JARVIS_WA_ALLOW_SEND=0" >> "$J/env"
fi
chmod 600 "$J/env"
command -v node > "$J/node_path"

echo "→ dependências"
(cd "$RAIZ/core" && uv sync --extra dev -q)
(cd "$RAIZ/bridge/whatsapp" && npm ci --silent && npm run build --silent)

echo "→ modelo local (Ollama)"
brew services start ollama >/dev/null 2>&1 || true
for i in {1..20}; do curl -sf http://127.0.0.1:11434/api/version >/dev/null && break; sleep 1; done
MODELO=$(grep -E '^modelo' "$J/jarvis.toml" | head -1 | cut -d'"' -f2)
ollama list | grep -q "^${MODELO:-qwen2.5:3b}" || ollama pull "${MODELO:-qwen2.5:3b}"

plist() {  # nome, programa, keepalive(true/false)
  cat > "$LA/com.jarvis.$1.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.jarvis.$1</string>
  <key>ProgramArguments</key><array><string>$2</string>${4:-}</array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><$3/>
  <key>ThrottleInterval</key><integer>15</integer>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>$J/logs/$1.log</string>
  <key>StandardErrorPath</key><string>$J/logs/$1.log</string>
</dict>
</plist>
PL
}

echo "→ serviços do launchd"
plist api "$RAIZ/scripts/bin/jarvis-api" true
plist agendador "$RAIZ/scripts/bin/jarvis-agendador" true
plist ponte "$RAIZ/scripts/bin/jarvis-ponte" true
plist abrir "$RAIZ/scripts/jarvis" false "<string>abrir</string>"
for s in api agendador ponte abrir; do
  launchctl bootout "gui/$UID_ATUAL/com.jarvis.$s" 2>/dev/null || true
  launchctl bootstrap "gui/$UID_ATUAL" "$LA/com.jarvis.$s.plist"
done

echo "→ comando e atalho"
ln -sf "$RAIZ/scripts/jarvis" "$HOME/.local/bin/jarvis"
osacompile -o "$HOME/Applications/Jarvis.app" -e "do shell script \"$RAIZ/scripts/jarvis abrir\"" 2>/dev/null \
  || { mkdir -p "$HOME/Applications" && osacompile -o "$HOME/Applications/Jarvis.app" -e "do shell script \"$RAIZ/scripts/jarvis abrir\""; }

echo "✓ Jarvis instalado. Ele sobe sozinho a cada login e abre a tela no navegador."
