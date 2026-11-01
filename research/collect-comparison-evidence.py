import base64
import concurrent.futures
import datetime
import json
import subprocess
from pathlib import Path

out = Path('.study-evidence')
out.mkdir(exist_ok=True)
def api(path):
    r = subprocess.run(['gh', 'api', path], capture_output=True, check=True)
    return json.loads(r.stdout)

def collect(repo):
    meta = api('repos/' + repo)
    release = api('repos/' + repo + '/releases/latest')
    issues = api('repos/' + repo + '/issues?state=all&sort=created&direction=desc&per_page=50')
    sample = [i for i in issues if 'pull_request' not in i][:10]
    for i in sample:
        comments = api('repos/' + repo + '/issues/' + str(i['number']) + '/comments?per_page=30') if i['comments'] else []
        i['sampled_comments'] = [{k:c[k] for k in ['html_url','created_at','author_association']} | {'user':c['user']['login'], 'type':c['user']['type']} for c in comments]
    data = {'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'repository':{k:meta[k] for k in ['full_name','html_url','default_branch','stargazers_count','forks_count','subscribers_count','open_issues_count','created_at','pushed_at','license']}, 'latest_release':{'tag_name':release['tag_name'],'published_at':release['published_at'],'html_url':release['html_url'],'assets':[{k:a[k] for k in ['name','size','download_count','browser_download_url']} for a in release['assets']]}, 'recent_issue_sample':[{k:i[k] for k in ['number','title','html_url','created_at','closed_at','state','comments','sampled_comments']} for i in sample]}
    (out / (repo.replace('/','-') + '.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(repo, 'evidence saved')

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(collect,['herdrdev/herdr','stablyai/orca']))

pin = 'b8ec5c8d170bcb9988e65de547a3a4e98b2885a9'
paths = ['package.json','docs/site/content/docs/remote-servers.mdx','docs/site/content/docs/ssh.mdx','skills/orchestration/SKILL.md','src/main/runtime/rpc/methods/orchestration/federation/federation-relay.ts']
for p in paths:
    try:
        data = api('repos/stablyai/orca/contents/' + p + '?ref=' + pin)
        target = out / 'orca-pinned' / p
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(base64.b64decode(data['content']))
    except subprocess.CalledProcessError:
        print('Unavailable source:', p)
