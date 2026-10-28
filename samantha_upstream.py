"""Propose an upstream stable snapshot; never merge, release or flash automatically."""
import json
from pathlib import Path
import subprocess


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


lock = json.loads(Path('samantha-lock.json').read_text())
release = json.loads(subprocess.check_output(['gh','api','repos/esphome/home-assistant-voice-pe/releases/latest'], text=True))
tag = release['tag_name']
if tag == lock['upstream_tag']:
    print(f'Already tracking official stable {tag}')
    raise SystemExit(0)
branch = f'upstream/stable-{tag}'
existing = json.loads(subprocess.check_output(['gh','pr','list','--head',branch,'--base','samantha','--json','number'],text=True))
if existing:
    print('Existing update PR:', existing)
    raise SystemExit(0)
git('fetch','https://github.com/esphome/home-assistant-voice-pe.git',f'refs/tags/{tag}')
commit = git('rev-parse','FETCH_HEAD^{commit}')
if git('ls-remote','--heads','origin',f'refs/heads/{branch}'):
    print(f'Existing update branch awaiting review: {branch}')
    raise SystemExit(0)
git('checkout','-b',branch)
old_paths = git('ls-tree','-r','--name-only',lock['upstream_commit']).splitlines()
new_paths = git('ls-tree','-r','--name-only',commit).splitlines()
# Preserve fork automation; synchronize every official runtime/source asset.
for name in old_paths:
    if not name.startswith('.github/') and name not in new_paths:
        subprocess.run(['git','rm','--ignore-unmatch','--',name],check=True)
for name in new_paths:
    if not name.startswith('.github/'):
        subprocess.run(['git','checkout',commit,'--',name],check=True)
lock['upstream_tag'] = tag
lock['upstream_commit'] = commit
lock['firmware_version'] = f'{tag}-samantha.1'
Path('samantha-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
p=Path('samantha.yaml')
import re
p.write_text(re.sub(r'firmware_version: "[^"]+"',f'firmware_version: "{lock["firmware_version"]}"',p.read_text()))
git('config','user.name','github-actions[bot]')
git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
git('add','samantha-lock.json','samantha.yaml')
git('commit','-m',f'Track official stable firmware {tag}')
git('push','origin',f'HEAD:refs/heads/{branch}')
Path('/tmp/samantha-upstream-pr.md').write_text(f'Update official runtime assets to [{tag}]({release["html_url"]}), commit `{commit}`. Keep Samantha overlay and vendored models.\n\nRun Samantha firmware on this branch and verify all checks before merging. Token-created PRs may require manually dispatching the workflow for this branch. No automatic release or device installation.\n')
result = subprocess.run(['gh','pr','create','--base','samantha','--head',branch,'--title',f'Track official stable firmware {tag}','--body-file','/tmp/samantha-upstream-pr.md'])
if result.returncode:
    print(f'Update branch pushed: {branch}. Repository policy prevented PR creation; open a PR from this branch manually. No merge or release performed.')
