"""Two isolated browser sessions against a deterministic Supabase API fixture.
Requires Python Playwright and Chromium. Does not contact or pair with production.
"""
import json,os,time,uuid,base64,re,datetime
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
from playwright.sync_api import sync_playwright
os.chdir(Path(__file__).resolve().parents[1])
state={n:[] for n in ['coop_devices','coop_game_state','coop_ratings','coop_suggestions','coop_responses']}
fail_write=False
scale=5
stamp=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')
def token(uid):
 enc=lambda o:base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip('=')
 return enc({'alg':'HS256','typ':'JWT'})+'.'+enc({'sub':uid,'exp':int(time.time())+7200,'role':'authenticated'})+'.signature'
def fixture(route):
 global fail_write
 req=route.request;url=urlparse(req.url);params=parse_qs(url.query);method=req.method
 if method=='OPTIONS':route.fulfill(status=204,headers={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'});return
 data=req.post_data_json if req.post_data else None
 def out(value,status=200):route.fulfill(status=status,content_type='application/json',body=json.dumps(value),headers={'access-control-allow-origin':'*','access-control-expose-headers':'content-range'})
 if url.path=='/auth/v1/signup':
  uid=str(uuid.uuid4());out({'access_token':token(uid),'refresh_token':'refresh-'+uid,'token_type':'bearer','expires_in':7200,'expires_at':int(time.time())+7200,'user':{'id':uid,'is_anonymous':True,'aud':'authenticated','app_metadata':{'provider':'anonymous'},'user_metadata':{}}});return
 bearer=req.headers.get('authorization','').removeprefix('Bearer ')
 try:uid=json.loads(base64.urlsafe_b64decode(bearer.split('.')[1]+'==='))['sub']
 except Exception:uid=None
 if url.path=='/rest/v1/rpc/coop_rating_scale':
  if scale==5:out({'code':'PGRST202','message':'Function not installed'},404)
  else:out(10)
  return
 if url.path=='/rest/v1/rpc/coop_save_rating_v10':
  if fail_write:out({'message':'Simulated save failure'},503);return
  m=next((r for r in state['coop_devices'] if r['user_id']==uid),None)
  if not m or m['display_name']!=data['p_profile_name']:out({'message':'Profile changed'},403);return
  r=next((r for r in state['coop_ratings'] if r['game_id']==data['p_game_id'] and r['profile_name']==m['display_name']),None)
  if r and r['updated_at']!=data['p_expected_updated_at']:out({'message':'Rating changed'},409);return
  if not r:r={'game_id':data['p_game_id'],'profile_name':m['display_name']};state['coop_ratings'].append(r)
  r.update(stars=data['p_score'],note=data['p_note'],positives=data['p_positives'],negatives=data['p_negatives'],updated_at=stamp());out(r);return
 if url.path=='/rest/v1/rpc/coop_pair_device':
  if not data.get('pairing_code') or data['pairing_code'] not in ['a'*32,'b'*32]:out({'message':'Invalid code'},400);return
  state['coop_devices'].append({'user_id':uid,'display_name':data['profile_name'],'last_seen_at':''});out(data['profile_name']);return
 table=url.path.split('/')[-1]
 if table not in state:out({'message':'Not mocked'},400);return
 member=next((r for r in state['coop_devices'] if r['user_id']==uid),None)
 def match(row):
  for k,vals in params.items():
   if vals[0].startswith('eq.') and str(row.get(k))!=vals[0][3:]:return False
  return table!='coop_devices' or row['user_id']==uid
 matches=[r for r in state[table] if match(r)]
 singular='application/vnd.pgrst.object+json' in req.headers.get('accept','')
 if method=='GET':
  if not member and table!='coop_devices':out([]);return
  out((matches[0] if matches else None) if singular else matches);return
 if fail_write:out({'message':'Simulated save failure'},503);return
 if not member:out({'message':'Not paired'},403);return
 if method=='PATCH':
  for row in matches:
   row.update(data)
   if table=='coop_game_state':row['revision']+=1
   row['updated_at']=stamp()
  out(matches if 'return=representation' in req.headers.get('prefer','') else None);return
 if method=='POST':
  result=[]
  for item in data if isinstance(data,list) else [data]:
   keys={'coop_game_state':['game_id'],'coop_ratings':['game_id','profile_name'],'coop_suggestions':['game_id','proposed_by'],'coop_responses':['suggestion_id','profile_name']}[table]
   new=dict(item)
   if table=='coop_suggestions':new.setdefault('proposed_by',member['display_name'])
   existing=next((r for r in state[table] if all(r.get(k)==new.get(k) for k in keys)),None)
   if existing:
    if 'resolution=ignore-duplicates' in req.headers.get('prefer',''):continue
    out({'code':'23505','message':'Duplicate record'},409);return
   new.setdefault('updated_at',stamp())
   if table=='coop_game_state':new.update(revision=1,updated_by=uid);new.setdefault('archived',False)
   if table=='coop_suggestions':new.update(id=str(uuid.uuid4()),created_at=stamp(),withdrawn=False)
   state[table].append(new);result.append(new)
  out((result[0] if singular and result else result) if 'return=representation' in req.headers.get('prefer','') else None,201);return
 out({'message':'Unsupported'},400)
server=ThreadingHTTPServer(('127.0.0.1',8765),SimpleHTTPRequestHandler);Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 contexts=[];pages=[];errors=[]
 for i in range(2):
  ctx=browser.new_context(viewport={'width':390,'height':844},accept_downloads=True);ctx.route('https://eoinghlgylynomxaqhji.supabase.co/**',fixture);ctx.route(re.compile(r'https://(?!eoinghlgylynomxaqhji.supabase.co).*'),lambda r:r.abort());page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.add_init_script("localStorage.setItem('coopAtlasGames',JSON.stringify([{id:900,name:'Local only game',genre:'Puzzle',mode:'Online',platforms:'PC',score:80,note:'Do not lose',playState:'Played',verdict:'Loved'}]));");page.goto('http://127.0.0.1:8765/');page.wait_for_selector('#syncSettings[open]');page.screenshot(path='/tmp/coop-pairing.png');page.get_by_role('button',name=['Fred','Manu'][i],exact=True).click();page.locator('#pairCode').fill(['a','b'][i]*32);page.get_by_role('button',name='Connect shared library',exact=True).click();page.wait_for_function("document.getElementById('profileButton').textContent==='"+['F','M'][i]+"'");page.wait_for_timeout(300);contexts.append(ctx);pages.append(page)
 a,b=pages
 assert not state['coop_game_state'],'Pairing uploaded local saves'
 a.evaluate("openGame(games.find(g=>g.playState==='Played').id)");assert a.locator('#sharedDetail').get_by_role('link',name='Apply the 1–10 ratings update').count()==1;assert a.locator('#ratingForm').count()==0;a.evaluate('closeGame()');scale=10;a.evaluate('CoopSync.refreshSettings()');b.evaluate('CoopSync.refreshSettings()')
 assert a.evaluate("JSON.parse(localStorage.getItem('coopAtlasGames'))[0].name")=='Local only game'
 a.evaluate("quickSet(1,'playState','Played')");a.wait_for_function("games.find(g=>g.id===1).playState==='Played'");a.wait_for_selector('#ratingPrompt[open]');a.screenshot(path='/tmp/coop-rating.png');assert not state['coop_ratings'];a.get_by_role('button',name='Not now',exact=True).click();assert not state['coop_ratings'];b.evaluate('CoopSync.refreshSettings()');b.wait_for_function("games.find(g=>g.id===1).playState==='Played'")
 a.evaluate('openGame(1)');a.locator('#ratingForm').get_by_role('button',name='9 out of 10',exact=True).click();a.locator('#ratingForm details').evaluate('(e)=>e.open=true');a.locator('#personalNote').fill('Fred liked this');fail_write=True;a.get_by_role('button',name='Save my rating').click();a.wait_for_timeout(300);assert a.locator('#personalNote').input_value()=='Fred liked this';fail_write=False;a.get_by_role('button',name='Save my rating').click();a.wait_for_timeout(400);a.locator('#ratingForm').get_by_role('button',name='8 out of 10',exact=True).click();a.get_by_role('button',name='Save my rating').click();a.wait_for_timeout(300)
 remote_rating=next(r for r in state['coop_ratings'] if r['profile_name']=='Fred');remote_rating.update(stars=7,note='Changed on another device',updated_at=stamp());a.evaluate('CoopSync.refreshSettings()');a.get_by_role('button',name='Save my rating').click();a.wait_for_timeout(300);assert remote_rating['stars']==7;assert a.locator('#personalNote').input_value()=='Fred liked this'
 b.evaluate('openGame(1)');b.locator('#ratingForm').get_by_role('button',name='6 out of 10',exact=True).click();b.get_by_role('button',name='Save my rating').click();b.wait_for_timeout(400);assert len(state['coop_ratings'])==2;assert {r['profile_name']:r['stars'] for r in state['coop_ratings']}=={'Fred':7,'Manu':6}
 a.evaluate('closeGame();openGame(2)');a.get_by_role('button',name='Should we play this?',exact=True).click();a.wait_for_timeout(400);assert len(state['coop_suggestions'])==1
 b.evaluate('closeGame();CoopSync.inbox()');b.wait_for_selector('#sharedInbox[open]');b.screenshot(path='/tmp/coop-inbox.png');b.get_by_role('button',name='Yes',exact=True).click();b.wait_for_timeout(400);assert state['coop_responses'][0]['response']=='yes';assert b.locator('#sharedInbox').inner_text().count('Portal 2')==1
 b.get_by_role('button',name='Pass',exact=True).click();b.wait_for_timeout(400);assert state['coop_responses'][0]['response']=='pass'
 b.evaluate("closeSheet('sharedInbox');CoopSync.settings()");b.get_by_role('button',name='Fred',exact=True).click();b.wait_for_timeout(400);assert b.locator('#profileButton').inner_text()=='F';b.get_by_role('button',name='Manu',exact=True).click();b.wait_for_timeout(300);b.evaluate("closeSheet('syncSettings')")
 a.evaluate('closeGame()');fail_write=True;a.evaluate("quickSet(2,'playState','Played')");a.wait_for_timeout(500);assert a.evaluate("games.find(g=>g.id===2).playState")=='Not played';assert a.evaluate("JSON.parse(localStorage.getItem('coopDbUnsavedChanges')).length")>=1;assert 'Simulated save failure' in a.locator('#sharedNotice').inner_text();fail_write=False
 a.evaluate("quickSet(3,'playState','Played')");a.wait_for_selector('#ratingPrompt[open]');a.get_by_role('button',name='Save rating',exact=True).click();assert 'Choose a score' in a.locator('#ratingPromptError').inner_text();a.locator('#ratingPrompt').get_by_role('button',name='10 out of 10',exact=True).click();a.locator('#ratingPrompt details').evaluate('(e)=>e.open=true');a.locator('#promptNote').fill('Great together');a.get_by_role('button',name='Save rating',exact=True).click();a.wait_for_timeout(400);assert any(r['game_id']=='seed:3' and r['stars']==10 and r['note']=='Great together' for r in state['coop_ratings']);assert not a.locator('#ratingPrompt').evaluate('(e)=>e.open')
 a.evaluate('CoopSync.settings()');a.on('dialog',lambda d:d.accept())
 with a.expect_download():a.get_by_role('button',name='Bring in this device’s local save').click()
 a.wait_for_timeout(500);assert any(r['game_data'].get('name')=='Local only game' for r in state['coop_game_state']);assert a.evaluate("JSON.parse(localStorage.getItem('coopAtlasGames'))[0].name")=='Local only game'
 a.evaluate("closeSheet('syncSettings')");a.reload();a.wait_for_timeout(700);assert a.locator('#profileButton').inner_text()=='F';assert not a.locator('#syncSettings').evaluate('(e)=>e.open')
 for width in [320,390,768,1440]:
  a.set_viewport_size({'width':width,'height':844});
  if a.evaluate('document.documentElement.scrollWidth>innerWidth'):print('overflow',width,a.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>[e.tagName,e.className,e.getBoundingClientRect().right]).slice(0,20)"))
  assert not a.evaluate('document.documentElement.scrollWidth>innerWidth'),width
 assert not errors,errors
 browser.close()
server.shutdown();print('PASS: two-device pairing, no automatic upload, shared play status, separate ratings, suggestions/responses, profile switching, save-failure recovery, explicit transfer, remembered session and responsive layout')
