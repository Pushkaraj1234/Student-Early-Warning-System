#!/usr/bin/env bash
# Builds the SEWS website (Flutter web) for Vercel or any Linux CI.
#
# Configuration comes ONLY from environment variables (Vercel: Project Settings -> Environment
# Variables), never from files in the repository:
#   SUPABASE_URL              https://<project-ref>.supabase.co
#   SUPABASE_PUBLISHABLE_KEY  the project's publishable (anon) key
# Everything compiled into a website is readable by every visitor, so a secret or
# service-role key is refused before building.
#
# Vercel's build image has no Flutter SDK; if `flutter` is not on PATH the pinned version is
# cloned first (needs git, curl and unzip).
set -euo pipefail

FLUTTER_VERSION="3.41.4" # the version the app is developed and tested with

fail() {
  echo "vercel_build: $*" >&2
  exit 1
}

[ -n "${SUPABASE_URL:-}" ] || fail "set SUPABASE_URL in the deployment environment variables"
[ -n "${SUPABASE_PUBLISHABLE_KEY:-}" ] || fail "set SUPABASE_PUBLISHABLE_KEY in the deployment environment variables"

case "$SUPABASE_URL" in
  https://*) ;;
  *) fail "SUPABASE_URL must be an https URL" ;;
esac

case "$SUPABASE_PUBLISHABLE_KEY" in
  sb_secret_*) fail "SUPABASE_PUBLISHABLE_KEY is a secret key; use the publishable (anon) key" ;;
esac
# Legacy JWT keys: refuse a token whose payload has the service_role role.
if [ "$(printf '%s' "$SUPABASE_PUBLISHABLE_KEY" | tr -cd '.' | wc -c)" -eq 2 ]; then
  payload="$(printf '%s' "$SUPABASE_PUBLISHABLE_KEY" | cut -d. -f2 | tr '_-' '/+')"
  while [ $(( ${#payload} % 4 )) -ne 0 ]; do payload="${payload}="; done
  if printf '%s' "$payload" | base64 -d 2>/dev/null | grep -q '"role" *: *"service_role"'; then
    fail "SUPABASE_PUBLISHABLE_KEY is a service-role key; use the publishable (anon) key"
  fi
fi

cd "$(dirname "$0")/.."

if ! command -v flutter >/dev/null 2>&1; then
  for tool in git curl unzip; do
    command -v "$tool" >/dev/null 2>&1 || fail "'$tool' is required to install Flutter"
  done
  FLUTTER_HOME="${FLUTTER_HOME:-$HOME/flutter-$FLUTTER_VERSION}"
  if [ ! -x "$FLUTTER_HOME/bin/flutter" ]; then
    git clone --depth 1 --branch "$FLUTTER_VERSION" https://github.com/flutter/flutter.git "$FLUTTER_HOME"
  fi
  export PATH="$FLUTTER_HOME/bin:$PATH"
fi

flutter --version
flutter pub get
# --csp: no dynamic code generation (needed for the Content-Security-Policy in vercel.json).
# --no-web-resources-cdn: CanvasKit is served from this site rather than a Google CDN.
flutter build web --release --csp --no-web-resources-cdn \
  --dart-define=SUPABASE_URL="$SUPABASE_URL" \
  --dart-define=SUPABASE_PUBLISHABLE_KEY="$SUPABASE_PUBLISHABLE_KEY"
