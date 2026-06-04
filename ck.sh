#!/usr/bin/env bash
set -eo pipefail

COMMAND="${1:-checkpoint}"

checkpoint() {
    local msg="${2:-$1}"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    if [[ -z "$msg" ]]; then
        read -rp "Checkpoint message: " msg
    fi

    if [[ -z "$msg" ]]; then
        echo "Error: message cannot be empty." >&2
        exit 1
    fi

    git add -A
    git commit -m "checkpoint: $msg [$timestamp]"
    echo "Checkpoint saved: $msg"
}

rollback() {
    echo ""
    echo "==================================================="
    echo " Recent commits:"
    echo "==================================================="
    git log --oneline --decorate -20
    echo "==================================================="
    echo ""
    read -rp "Commit hash to roll back to (or Enter to cancel): " target

    if [[ -z "$target" ]]; then
        echo "Cancelled."
        exit 0
    fi

    if ! git cat-file -e "${target}^{commit}" 2>/dev/null; then
        echo "Error: commit not found: $target" >&2
        exit 1
    fi

    echo ""
    echo "WARNING: This will discard all uncommitted changes."
    read -rp "Are you sure? [y/N] " confirm
    if [[ "${confirm,,}" != "y" ]]; then
        echo "Cancelled."
        exit 0
    fi

    git reset --hard "$target"
    echo "Rolled back to $target."
}

case "$COMMAND" in
    rb) rollback ;;
    *)  checkpoint "$@" ;;
esac
