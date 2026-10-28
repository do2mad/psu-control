#!/bin/bash
# SPDX-License-Identifier: MIT
#
# Legt das GitHub-Repository fuer PSU Control an und laedt alles hoch.
# Creates the GitHub repository for PSU Control and pushes everything.
#
#   ./tools/publish-github.sh <github-name> [repo-name]
#   ./tools/publish-github.sh martin psu-control
#
# Mit installierter GitHub CLI (brew install gh; gh auth login) wird das
# Repository automatisch angelegt. Ohne gh: leeres Repository auf github.com
# anlegen (ohne README/Lizenz), dann dieses Skript starten.
set -euo pipefail

GH_USER="${1:-}"
REPO="${2:-psu-control}"
if [ -z "$GH_USER" ]; then
  echo "Aufruf / usage: $0 <github-name> [repo-name]" >&2
  exit 1
fi
cd "$(dirname "$0")/.."
VERSION="$(cat VERSION)"

echo "→ Platzhalter ersetzen: GITHUB_USER → $GH_USER, Repository → $REPO"
grep -rl --include='*.md' --exclude-dir=.git 'GITHUB_USER' . | while read -r f; do
  perl -pi -e "s#github\.com/GITHUB_USER/psu-control#github.com/$GH_USER/$REPO#g; s#GITHUB_USER#$GH_USER#g" "$f"
done

if [ ! -d .git ]; then
  echo "→ git init"
  git init -q -b main
fi
git add -A
if git diff --cached --quiet; then
  echo "→ nichts Neues zu committen"
else
  git commit -q -m "PSU Control $VERSION"
  echo "→ Commit: PSU Control $VERSION"
fi

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  if ! git remote get-url origin >/dev/null 2>&1; then
    echo "→ Repository $GH_USER/$REPO auf GitHub anlegen"
    gh repo create "$GH_USER/$REPO" --public --source . --remote origin \
      --description "Remote control for the UNI-T UDP3305S-E bench power supply – Mac, iPhone, iPad" \
      --homepage "https://github.com/$GH_USER/$REPO"
  fi
else
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/$GH_USER/$REPO.git"
  fi
  echo "   (GitHub CLI nicht gefunden – Repository $GH_USER/$REPO bitte vorher auf github.com anlegen, leer)"
fi

echo "→ Hochladen"
git push -u origin main

if ! git rev-parse "v$VERSION" >/dev/null 2>&1; then
  git tag "v$VERSION"
fi
git push origin "v$VERSION"

echo
echo "Fertig / done:  https://github.com/$GH_USER/$REPO"
echo "GitHub Actions baut jetzt die Mac-App und legt das Release v$VERSION an:"
echo "               https://github.com/$GH_USER/$REPO/actions"
echo "Datenschutz-URL für App Store Connect:"
echo "               https://github.com/$GH_USER/$REPO/blob/main/PRIVACY.md"
