const setupQueries={ratings:'./supabase/003_ratings_out_of_ten.sql',schema:'./supabase/001_shared_library.sql',codes:'./supabase/002_generate_pairing_codes.sql'};
for(const button of document.querySelectorAll('[data-copy]')){
  const name=button.dataset.copy;
  fetch(setupQueries[name]).then(r=>{if(!r.ok)throw Error('Could not load SQL');return r.text()}).then(sql=>{
    button.disabled=false;button.textContent=name==='schema'?'Copy database setup SQL':name==='ratings'?'Copy 1–10 ratings update SQL':'Copy pairing-code SQL';
    // Fetch before the tap: Safari clipboard writes need the original user gesture.
    button.onclick=()=>{
      const fallback=()=>{const area=document.getElementById('manualCopy');area.hidden=false;area.value=sql;area.focus();area.select();document.getElementById('copyStatus').textContent='Select and copy the SQL from the text box below.'};
      if(!navigator.clipboard){fallback();return}
      navigator.clipboard.writeText(sql).then(()=>{document.getElementById('copyStatus').textContent='SQL copied. Paste it into a new Supabase SQL Editor query.';button.textContent='Copied ✓'},fallback);
    };
  }).catch(()=>{button.textContent='Use the View SQL link';document.getElementById('copyStatus').textContent='SQL could not load. Open View SQL to copy it manually.'});
}
