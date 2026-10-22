"""Remote stdio entry: SSH access selects one preconfigured fixed identity."""
import json,os,pathlib,shlex,sys
if len(sys.argv)!=2 or sys.argv[1] not in ('blue','red'):
 raise SystemExit('Select blue or red MCP session')
vals={}
for line in pathlib.Path('/opt/ibs-bot/bot.env').read_text().splitlines():
 if not line.strip() or line.lstrip().startswith('#'):continue
 key,separator,raw=line.partition('=')
 if not separator:raise SystemExit('Invalid private service configuration')
 parts=shlex.split(raw,comments=True)
 vals[key.strip()]=parts[0] if parts else ''
identity=vals.get('IBS_MCP_'+sys.argv[1].upper()+'_IDENTITY','agent:'+sys.argv[1])
tokens=[token for token,actor in json.loads(vals['IBS_AGENT_IDENTITIES']).items() if actor==identity]
if len(tokens)!=1:raise SystemExit('Fixed MCP identity is not configured')
os.environ['IBS_BOT_URL']='http://127.0.0.1:13192'
os.environ['IBS_AGENT_TOKEN']=tokens[0]
from iron_bottom_sound.bot.mcp_server import main
main()
