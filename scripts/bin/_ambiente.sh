#!/bin/zsh
# Carrega o token e os caminhos para os serviços do launchd.
export JARVIS_HOME="$HOME/.jarvis"
export JARVIS_RAIZ="$HOME/jarvis"
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
[ -f "$JARVIS_HOME/env" ] && set -a && source "$JARVIS_HOME/env" && set +a
