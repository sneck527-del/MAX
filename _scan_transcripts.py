import json, sys, re
from collections import Counter
from pathlib import Path

projects_dir = Path.home() / ".claude" / "projects"

files = []
for f in sorted(projects_dir.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
    if "subagents" not in f.parts:
        files.append(f)
    if len(files) >= 50:
        break

# AUTO-ALLOWED (skip these - never prompt)
AUTO_BASE = {'cal','uptime','cat','head','tail','wc','stat','strings','hexdump','od','nl',
    'id','uname','free','df','du','locale','groups','nproc','basename','dirname',
    'realpath','cut','paste','tr','column','tac','rev','fold','expand','unexpand',
    'fmt','comm','cmp','numfmt','readlink','diff','true','false','sleep','which',
    'type','expr','test','getconf','seq','tsort','pr','echo','printf','ls','cd','find',
    'pwd','whoami','alias','xargs','file','sed','sort','man','help','netstat','ps',
    'base64','grep','egrep','fgrep','sha256sum','sha1sum','md5sum','tree','date',
    'hostname','info','lsof','pgrep','tput','ss','fd','fdfind','aki','rg','jq',
    'uniq','history','arch','ifconfig','pyright'}
GIT_RO = ('status','log','diff','show','blame','branch','tag','remote','ls-files',
          'ls-remote','rev-parse','describe','stash','reflog','shortlog','cat-file',
          'for-each-ref','worktree','check-ignore','check-attr')

def is_auto(cmd):
    parts = cmd.strip().split()
    if not parts: return True
    base = parts[0].lower()
    if base in AUTO_BASE: return True
    if base == 'git' and len(parts) > 1 and parts[1] in GIT_RO: return True
    if base == 'gh' and len(parts) > 2 and parts[2] in ('view','list','diff','checks','status'): return True
    if base == 'docker' and len(parts) > 1 and parts[1] in ('ps','images','logs','inspect'): return True
    if cmd.strip() in ('claude -h','claude --help','node -v','node --version','python --version','python3 --version','ip addr'): return True
    return False

# Also drop these mutation/destructive commands entirely
DANGEROUS_BASES = {'rm','rmdir','mv','cp','chmod','chown','kill','taskkill','pkill',
                   'killall','shutdown','reboot','dd','format','mkfs','fdisk','iptables',
                   'reg','regedit','takeown','icacls','attrib', 'del', 'deltree',
                   'git push','git commit','git merge','git rebase','git reset','git revert',
                   'git cherry-pick','git add','git rm', 'pip install','pip uninstall',
                   'npm install','npm publish','yarn add','yarn remove','bun add','bun remove',
                   'docker run','docker exec','docker build','docker compose up',
                   'kubectl apply','kubectl delete','kubectl create','terraform apply',
                   'az','aws s3 cp','aws s3 sync','gsutil cp','gsutil rsync',
                   'write','Write', 'mkdir'}

cmd_counter = Counter()
pattern_counter = Counter()
mcp_counter = Counter()

for fpath in files:
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: obj = json.loads(line)
                except: continue
                if not isinstance(obj, dict) or obj.get("type") != "assistant": continue
                msg = obj.get("message", {})
                if not isinstance(msg, dict): continue
                for entry in msg.get("content", []):
                    if not isinstance(entry, dict) or entry.get("type") != "tool_use": continue
                    name = entry.get("name", "")
                    inp = entry.get("input", {})
                    if not isinstance(inp, dict): continue
                    if name == "Bash":
                        cmd = inp.get("command", "")
                        if not isinstance(cmd, str) or not cmd.strip(): continue
                        if is_auto(cmd): continue
                        parts = cmd.strip().split()
                        base = parts[0].lower()
                        if base in DANGEROUS_BASES: continue
                        # Check for second word too
                        if len(parts) > 1 and f"{base} {parts[1].lower()}" in DANGEROUS_BASES: continue
                        # Skip python/node/etc - arbitrary code execution
                        if base in ('python','python3','node','bun','deno','ruby','perl','php','lua','npx','bunx','uvx','sudo','eval','exec'): continue
                        # Skip pip
                        if base == 'pip' and len(parts) > 1 and parts[1] in ('install','uninstall'): continue
                        # Skip powershell (can do anything)
                        if base in ('powershell','pwsh'): continue
                        # Skip start
                        if base == 'start': continue
                        # Skip heredocs and multi-line scripts
                        if cmd.strip().startswith('#!/') or cmd.strip().startswith('<<'): continue

                        cmd_counter[cmd.strip()] += 1

                        # Create pattern
                        if len(parts) == 1:
                            pattern = f"Bash({base}:*)"
                        elif len(parts) >= 2 and base in ('git','gh','docker','pip','npm','bun','cargo','go','make','just','kubectl','curl','wget','b2','az','gcloud','winget','choco','scoop','brew'):
                            pattern = f"Bash({base} {parts[1]}:*)"
                        else:
                            # For tools like tasklist, mkdir with args
                            pattern = f"Bash({base}:*)"
                        pattern_counter[pattern] += 1
                    elif name.startswith("mcp__"):
                        mcp_counter[name] += 1

# Output
if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, closefd=False)

sys.stdout.write("=== READ-ONLY BASH (individual commands) ===\n")
for cmd, count in cmd_counter.most_common(30):
    sys.stdout.write(f"{count}\t{cmd[:200]}\n")

sys.stdout.write("\n=== PATTERNS ===\n")
for pat, count in pattern_counter.most_common(30):
    sys.stdout.write(f"{count}\t{pat}\n")

sys.stdout.write("\n=== MCP TOOLS ===\n")
for name, count in mcp_counter.most_common(30):
    sys.stdout.write(f"{count}\t{name}\n")
