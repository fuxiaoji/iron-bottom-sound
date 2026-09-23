#!/usr/bin/env bash
# 把本仓库推到 GitHub，且**不会**把误提交的重型路径推上去。
#
# 为什么需要这个脚本：历史里有两个包袱，直接 `git push` 必被 GitHub 拒绝——
#
#   1. `.venv_phase_a/`（616 MB / 20645 个文件，由 commit acfbb4f9 引入）
#      一个虚拟环境目录。`.venv/` 本来就在 .gitignore 里，所以这份显然是误提交。
#   2. `research/m1_5/metrics/e2_t1_decisions.json`（124 MB 与 83 MB 两个版本）
#      超过 GitHub 的单文件 100 MB 硬上限。
#
# 做法：在一个临时克隆里用 filter-branch 把这 79 个提交中的上述路径摘掉，再推。
# **本地仓库一个字节都不改**：不重写本地 refs、不动工作区（本地仍保留 venv 与那份 metrics）。
# 代价是远端那几个提交的 SHA 与本地不同——本地是权威历史，远端是可发布历史。
#
# 用法：
#   scripts/push_to_github.sh              # 真正推送
#   scripts/push_to_github.sh --dry-run    # 只算要传多少、检查超限，不推
#   BRANCH=my/branch scripts/push_to_github.sh
set -euo pipefail

REMOTE_URL="${REMOTE_URL:-https://github.com/fuxiaoji/iron-bottom-sound.git}"
BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
BASE="${BASE:-origin/codex/v14-budgeted-replanning}"
# 远端也一并快进更新的分支名（留空则只推 BRANCH 一个引用）
ALSO_UPDATE="${ALSO_UPDATE-codex/v14-budgeted-replanning}"
DROP=(.venv_phase_a research/m1_5/metrics/e2_t1_decisions.json)
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "== 待推范围 $BASE..$BRANCH =="
git rev-list --count "$BASE..$BRANCH" | xargs echo "提交数:"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/ibs-push.XXXXXX")"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

echo "== 临时克隆（--shared，不复制对象）: $WORK =="
git clone --shared -q "$REPO_ROOT" "$WORK"
cd "$WORK"
git remote set-url origin "$REMOTE_URL"

echo "== 从范围内摘除: ${DROP[*]} =="
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f \
  --index-filter "git rm -r --cached --ignore-unmatch -q ${DROP[*]}" \
  -- "$BASE..HEAD" >/dev/null
git for-each-ref --format='%(refname)' refs/original | xargs -r -n1 git update-ref -d

echo "== 超限检查（GitHub 单文件上限 100 MB）=="
OVER=$(git rev-list --objects HEAD | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' \
       | awk '$1=="blob" && $2 > 100*1048576 {print $3}' | sort -u)
if [[ -n "$OVER" ]]; then
  echo "仍存在超限文件，需先加入 DROP 列表："; echo "$OVER"; exit 1
fi
git rev-list --objects "$BASE..HEAD" | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' \
  | awk '$1=="blob"{s+=$2; n++} END {printf "本次将上传: %.0f MB / %d 个新对象\n", s/1048576, n}'

if [[ "$DRY_RUN" == 1 ]]; then
  echo "--dry-run：到此为止，未推送。"
  exit 0
fi

echo "== 推送 =="
git push "$REMOTE_URL" "HEAD:refs/heads/$BRANCH"
if [[ -n "$ALSO_UPDATE" && "$ALSO_UPDATE" != "$BRANCH" ]]; then
  git push "$REMOTE_URL" "HEAD:refs/heads/$ALSO_UPDATE"
fi
echo "完成。本地仓库未做任何修改。"
