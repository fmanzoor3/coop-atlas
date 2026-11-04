"""Local-library UI and data portability smoke test. No production connections."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
import os,json,re,subprocess
from playwright.sync_api import sync_playwright
os.chdir(Path(__file__).resolve().parents[1])
server=ThreadingHTTPServer(('127.0.0.1',8765),SimpleHTTPRequestHandler);Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def asset(route):
  shots_path=Path('/tmp/coop-polish-art/shots.json')
  shots=json.loads(shots_path.read_text()) if shots_path.exists() else {}
  if route.request.url in shots:route.fulfill(path=shots[route.request.url],content_type='image/jpeg');return
  m=re.search(r'/apps/(\d+)/header.jpg',route.request.url)
  if m and (Path('/tmp/coop-polish-art')/(m[1]+'.jpg')).exists():route.fulfill(path=str(Path('/tmp/coop-polish-art')/(m[1]+'.jpg')),content_type='image/jpeg')
  else:route.abort()
 page.route('https://**/*',asset);page.goto('http://127.0.0.1:8765/');page.get_by_role('button',name='Use local saves',exact=True).click();page.screenshot(path='/tmp/polished-discover.png')
 assert page.evaluate("localStorage.getItem('coopAtlasGames')") is None
 page.evaluate("setTab('all')");assert page.locator('.card').count()==167
 page.locator('#search').fill('Portal 2');assert page.locator('.card').count()==1;page.locator('#search').fill('')
 page.locator('#filterButton').click();page.locator('#platform').select_option('PC');page.locator('#genre').select_option('Puzzle');page.locator('#sort').select_option('name');page.locator('#showResults').click();assert page.locator('.card').count()>0;assert all('PC' in x for x in page.locator('.card-platforms').all_inner_texts());page.evaluate('resetFilters(true)')
 page.get_by_role('button',name='Open app menu').click();assert page.locator('#menuStats').is_hidden();page.get_by_role('button',name='Add a game',exact=False).click();assert page.locator('#gameMeta').evaluate('(e)=>e.open');page.locator('#editName').fill('Audit test game');page.locator('#editGenre').fill('Puzzle');page.locator('#editPlatforms').fill('PC');page.locator('#editNote').fill('Original note');page.get_by_role('button',name='Save game',exact=True).click();assert page.evaluate('games.length')==168
 gid=page.evaluate("games.find(g=>g.name==='Audit test game').id");page.evaluate(f"games.find(g=>g.id==={gid}).genre=''");page.evaluate(f'editGame({gid})');assert not page.locator('#gameMeta').evaluate('(e)=>e.open');assert page.locator('#editStatus').is_hidden();page.locator('#editNote').fill('Edited note');page.locator('#editPlayState').select_option('Played');page.get_by_role('button',name='Save game',exact=True).click();assert page.locator('#gameMeta').evaluate('(e)=>e.open');page.locator('#editGenre').fill('Puzzle');page.get_by_role('button',name='Save game',exact=True).click();assert page.evaluate(f'games.find(g=>g.id==={gid}).note')=='Edited note'
 with page.expect_download() as info:page.evaluate('exportData()')
 info.value.save_as('/tmp/polish-backup.json');data=json.loads(Path('/tmp/polish-backup.json').read_text());assert len(data['games'])==168
 page.on('dialog',lambda d:d.accept());page.locator('#import').set_input_files('/tmp/polish-backup.json');page.wait_for_timeout(100);assert json.loads(page.evaluate("localStorage.getItem('coopAtlasGames')"))==data['games'];page.reload();page.wait_for_timeout(300);assert page.evaluate('games.length')==168
 page.get_by_role('button',name='List view',exact=True).click();page.reload();page.wait_for_timeout(200);assert page.locator('#cards').evaluate("e=>e.classList.contains('is-list')");page.get_by_role('button',name='Grid view',exact=True).click()
 # Detailed guidance remains; no generic genre-derived assessment is invented.
 page.evaluate(f'openGame({gid})');assert page.locator('.assessment').count()==0;page.evaluate("announce('Visible test')");assert page.locator('#toast').evaluate("(e)=>e.closest('dialog').id")=='gameDialog';assert page.locator('#toast').is_visible();page.evaluate('closeGame();openGame(1)');assert page.locator('.assessment-row').count()==5;
 if Path('/tmp/coop-polish-art/shots.json').exists():page.locator('.shot').first.click()
 else:page.evaluate('openLightbox(0)')
 assert page.locator('#lightbox').evaluate('(e)=>e.open');page.keyboard.press('ArrowRight');assert '2 of 2' in page.locator('#lightboxCount').inner_text();page.keyboard.press('Escape');assert page.locator('#gameDialog').evaluate('(e)=>e.open');page.evaluate('closeGame()')
 for width in [320,375,390,430,768,1024,1440]:
  page.set_viewport_size({'width':width,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),width
 assert not errors,errors;b.close()
server.shutdown();print('PASS: local saves, all-game browsing, search/filters/sort, simplified add/edit, legacy field compatibility, export/import, assessments, visible dialog feedback and responsive widths')
