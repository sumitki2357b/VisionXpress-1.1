const state = { token: localStorage.getItem('vx_token') || '', user: JSON.parse(localStorage.getItem('vx_user') || 'null'), page: 'dashboard', planningDate: localStorage.getItem('vx_date') || '2026-09-01', blocks: [], requests: [] };
const $ = (s) => document.querySelector(s);
const main = $('#main-view');

async function api(path, options = {}) {
  const headers = options.headers ? {...options.headers} : {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (!(options.body instanceof FormData) && options.body !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch(path, {...options, headers});
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = {detail: text}; }
  if (response.status === 401) { logout(false); }
  if (!response.ok) throw Object.assign(new Error(data.detail || 'Request failed'), {status: response.status, data});
  return data;
}

function toast(message, type='info') {
  const el = document.createElement('div'); el.className = `toast ${type}`; el.textContent = message; $('#toast-root').appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function fmt(value) { return value == null || value === '' ? 'Not provided' : String(value); }
function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function priorityClass(p='LOW'){ return p.toLowerCase(); }
function initials(text){ return String(text||'VX').slice(0,2).toUpperCase(); }

function showApp() {
  $('#login-view').classList.add('hidden'); $('#app-view').classList.remove('hidden');
  $('#user-name').textContent = state.user.user_id; $('#user-department').textContent = state.user.department;
  $('#user-avatar').textContent = initials(state.user.department); $('#planning-date').value = state.planningDate;
  buildNav(); renderPage(); refreshNotifications();
}
function showLogin(){ $('#app-view').classList.add('hidden'); $('#login-view').classList.remove('hidden'); }
function logout(server=true){ if(server) api('/api/auth/logout',{method:'POST'}).catch(()=>{}); state.token=''; state.user=null; localStorage.removeItem('vx_token'); localStorage.removeItem('vx_user'); showLogin(); }

function buildNav(){
  const d=state.user.department; const items=[['dashboard','Dashboard']];
  if(['TMS','TDMS','SMMS'].includes(d)){items.push(['submit','Submit Request'],['track','Track Request']);}
  if(d==='COA') items.push(['coa','COA Schedule']);
  if(d==='TDMS' || d==='BDMS') items.push(['blocks','Block Dashboard']);
  if(d==='BDMS') items.push(['approvals','BDMS Approvals']);
  items.push(['notifications','Alerts']);
  $('#nav-menu').innerHTML=items.map(([id,label])=>`<button class="nav-item ${state.page===id?'active':''}" data-page="${id}">${label}</button>`).join('');
  document.querySelectorAll('.nav-item').forEach(b=>b.onclick=()=>{state.page=b.dataset.page;renderPage();buildNav();});
}

async function renderPage(){
  const labels={dashboard:'CONTROL CENTER',submit:'MAINTENANCE REQUEST',track:'REQUEST TRACKING',coa:'COA OPERATIONS',blocks:'BLOCK CONTROL',approvals:'BDMS DECISION DESK',notifications:'NOTIFICATIONS'};
  $('#page-kicker').textContent=labels[state.page]||'CONTROL CENTER';
  $('#page-title').textContent=state.page==='dashboard'?'Dashboard':state.page[0].toUpperCase()+state.page.slice(1);
  main.innerHTML='<div class="loading">Loading control view…</div>';
  try {
    if(state.page==='dashboard') return await renderDashboard();
    if(state.page==='submit') return renderSubmit();
    if(state.page==='track') return renderTrack();
    if(state.page==='coa') return await renderCOA();
    if(state.page==='blocks') return await renderBlocks();
    if(state.page==='approvals') return await renderApprovals();
    if(state.page==='notifications') return await renderNotifications();
  } catch(e){ main.innerHTML=`<div class="panel"><div class="danger-text">${escapeHtml(e.message)}</div></div>`; }
}

async function renderDashboard(){
  const data=await api(`/api/dashboard?planning_date=${state.planningDate}`);
  const blocks=data.blocks||[];
  const reqs=data.requests||[];
  main.innerHTML=`
    <div class="stats-grid">
      <div class="stat-card"><div class="label">Planning date</div><div class="value" style="font-size:19px">${escapeHtml(state.planningDate)}</div><div class="hint">Active control window</div></div>
      <div class="stat-card"><div class="label">Recommended blocks</div><div class="value">${blocks.filter(b=>b.status==='PENDING_APPROVAL'||b.status==='RECOMMENDED').length}</div><div class="hint">Awaiting decision</div></div>
      <div class="stat-card"><div class="label">Approved</div><div class="value">${blocks.filter(b=>b.status==='APPROVED').length}</div><div class="hint">Confirmed blocks</div></div>
      <div class="stat-card"><div class="label">Tasks</div><div class="value">${data.scheduled_tasks||0}</div><div class="hint">In current workflow</div></div>
      <div class="stat-card"><div class="label">System status</div><div class="value success-text" style="font-size:19px">SAFE</div><div class="hint">0 known resource conflicts</div></div>
    </div>
    <div class="two-col" style="margin-top:16px">
      <section class="panel"><div class="section-title"><h3>${state.user.department==='TDMS'?'Recommended maintenance blocks':'Your request activity'}</h3><span>${state.user.department==='TDMS'?'Sorted by urgency':'Latest activity'}</span></div>
        ${state.user.department==='TDMS'?renderBlockCards(blocks.slice(0,8),true):renderRequestCards(reqs.slice(0,8))}
      </section>
      <section class="panel"><div class="section-title"><h3>Quick actions</h3><span>Operator shortcuts</span></div>${quickActions()}</section>
    </div>`;
}
function quickActions(){
  const d=state.user.department;
  if(['TMS','TDMS','SMMS'].includes(d)) return `<div class="block-list"><button class="primary wide" onclick="go('submit')">Submit maintenance request</button><button class="secondary wide" onclick="go('track')">Track a request by Task ID</button>${d==='TDMS'?'<button class="secondary wide" onclick="go(\'blocks\')">Open block dashboard</button>':''}</div>`;
  if(d==='COA') return `<div class="block-list"><button class="primary wide" onclick="go('coa')">Upload COA schedule</button><button class="secondary wide" onclick="go('notifications')">View block alerts</button></div>`;
  return `<div class="block-list"><button class="primary wide" onclick="loadDemo()">Load synthetic demo data</button><button class="primary wide" onclick="generatePlan()">Generate / refresh block plan</button><button class="secondary wide" onclick="go('approvals')">Open pending approvals</button><button class="secondary wide" onclick="go('blocks')">Review all blocks</button></div>`;
}
function go(page){state.page=page;buildNav();renderPage();}

function renderBlockCards(blocks, canReview=false){
  if(!blocks.length) return '<div class="empty">No blocks available for this planning date.</div>';
  return `<div class="block-list">${blocks.map(b=>`<div class="block-card"><div class="block-main"><div class="block-top"><span class="pill ${priorityClass(b.priority)}">${escapeHtml(b.priority)}</span><span class="pill">${escapeHtml(b.status.replaceAll('_',' '))}</span>${b.coordination?'<span class="pill">COORDINATED</span>':''}</div><div class="block-time">${escapeHtml(b.start_time)} → ${escapeHtml(b.end_time)}</div><div class="block-meta">${escapeHtml(b.section_id)} · Score ${Number(b.priority_score).toFixed(0)} · ${b.tasks.length} task${b.tasks.length===1?'':'s'}</div></div><div class="block-actions"><button class="small-btn" onclick="openBlock('${escapeHtml(b.block_id)}')">Details</button>${canReview&&b.status==='PENDING_APPROVAL'?`<button class="small-btn" onclick="openModify('${escapeHtml(b.block_id)}')">Modify</button>`:''}</div></div>`).join('')}</div>`;
}
function renderRequestCards(reqs){ if(!reqs.length)return '<div class="empty">No request activity yet.</div>'; return `<div class="request-list">${reqs.map(r=>`<div class="block-card"><div><div class="block-top"><span class="pill">${escapeHtml(r.request_id)}</span><span class="pill">${escapeHtml(r.status)}</span></div><div class="block-meta">${escapeHtml(r.section_id)} · ${escapeHtml(r.work_description||'')}</div></div><button class="small-btn" onclick="trackTask('${escapeHtml(r.request_id)}')">View</button></div>`).join('')}</div>`; }

function renderSubmit(){
  main.innerHTML=`<section class="panel"><div class="section-title"><h3>Submit a maintenance request</h3><span>Manual entry or CSV/XLSX import</span></div><div class="upload-zone"><div class="eyebrow">FAST IMPORT</div><h3 style="margin:8px 0">Upload a populated maintenance file</h3><p class="muted">The backend validates headers, values, dates, times, section IDs and duplicates before anything is saved.</p><label for="maint-file">Choose CSV / XLSX</label><input id="maint-file" type="file" accept=".csv,.xlsx,.xlsm" /><div class="upload-info" id="maint-file-name">No file selected</div><div class="form-actions"><button class="secondary" type="button" onclick="downloadMaintenanceTemplate()">Download template</button><button class="primary" onclick="uploadMaintenance()">Validate & submit</button></div></div><div id="maint-upload-result"></div><div class="section-title" style="margin-top:28px"><h3>Or enter details manually</h3><span>All safety-relevant fields are validated server-side</span></div>${manualForm()}</section>`;
  $('#maint-file').onchange=()=>$('#maint-file-name').textContent=$('#maint-file').files[0]?.name||'No file selected';
  $('#manual-form').onsubmit=submitManual;
}
function manualForm(){const fields=[['location','Station / location'],['section_id','Section ID'],['asset_id','Asset ID'],['asset_type','Asset type'],['maintenance_category','Maintenance category'],['defect_id','Defect ID'],['defect_severity','Defect severity'],['failure_risk','Failure risk'],['asset_operational_status','Asset operational status'],['affected_asset_quantity','Affected asset quantity'],['last_maintenance_date','Last maintenance date'],['due_date','Due date'],['estimated_duration_minutes','Estimated duration (minutes)'],['required_resources','Required resources'],['block_type_required','Block type'],['preferred_date','Preferred date'],['preferred_start_time','Preferred start time'],['preferred_end_time','Preferred end time']];return `<form id="manual-form" class="form-grid"><div class="full"><label>Work description</label><textarea name="work_description" required placeholder="Describe the maintenance work precisely"></textarea></div>${fields.map(([name,label])=>`<div><label>${label}</label>${['defect_severity','failure_risk'].includes(name)?`<select name="${name}" required><option value="">Select</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select>`:name==='asset_operational_status'?`<select name="${name}" required><option>OPERATIONAL</option><option>RESTRICTED</option><option>DEGRADED</option><option>FAILED</option><option>NORMAL</option></select>`:name==='block_type_required'?`<select name="${name}" required><option>PARTIAL</option><option>FULL</option></select>`:name.includes('date')?`<input type="date" name="${name}">`:name.includes('time')?`<input type="time" name="${name}">`:`<input name="${name}" ${['location','section_id','asset_id','asset_type','maintenance_category','defect_severity','failure_risk','asset_operational_status','estimated_duration_minutes'].includes(name)?'required':''}>`}</div>`).join('')}<div><label>Safety related</label><select name="safety_related" required><option value="false">No</option><option value="true">Yes</option></select></div><div><label>Requires block</label><select name="requires_block" required><option value="true">Yes</option><option value="false">No</option></select></div><div><label>Overdue</label><select name="overdue" required><option value="false">No</option><option value="true">Yes</option></select></div><div class="form-actions full"><button class="secondary" type="reset">Clear</button><button class="primary" type="submit">Submit request</button></div></form>`;}
async function submitManual(ev){ev.preventDefault();const data={};new FormData(ev.target).forEach((v,k)=>data[k]=v);for(const k of ['safety_related','requires_block','overdue']) data[k]=data[k]==='true';for(const k of ['affected_asset_quantity','estimated_duration_minutes'])if(data[k]!=='')data[k]=Number(data[k]);try{const result=await api('/api/maintenance/manual',{method:'POST',body:JSON.stringify(data)});toast(`Request ${result.request.request_id} submitted`,'success');ev.target.reset();}catch(e){showValidation(e.data||{errors:[e.message]},'maint-upload-result');toast('Please correct the validation errors','error');}}
function showValidation(data,target){const t=document.getElementById(target);t.innerHTML=`<div class="validation-box"><strong>${data.valid===false?'Validation failed':'Validation result'}</strong>${(data.errors||[]).map(x=>typeof x==='string'?`<div class="error-row"><div>${escapeHtml(x)}</div></div>`:`<div class="error-row"><strong>Row ${escapeHtml(x.row)} ${x.request_id||x.train_id?`· ${escapeHtml(x.request_id||x.train_id)}`:''}</strong><div>${escapeHtml((x.errors||[]).join(' · '))}</div></div>`).join('')}</div>`;}
async function uploadMaintenance(){const file=$('#maint-file').files[0];if(!file)return toast('Select a file first','error');const fd=new FormData();fd.append('file',file);try{const r=await api('/api/maintenance/upload',{method:'POST',body:fd});$('#maint-upload-result').innerHTML=`<div class="validation-box"><div class="success-text">✓ ${r.saved} maintenance request(s) accepted and submitted.</div></div>`;toast('Maintenance file accepted','success');}catch(e){showValidation(e.data||{errors:[e.message]},'maint-upload-result');}}

function renderTrack(){main.innerHTML=`<section class="panel"><div class="section-title"><h3>Track your request</h3><span>Search using Task ID</span></div><div class="search-row"><input class="search-input" id="track-input" placeholder="Example: TMS-036" /><button class="primary" onclick="trackTask($('#track-input').value)">Track</button></div><div id="track-result"></div></section>`;}
async function trackTask(taskId){taskId=(taskId||'').trim();if(!taskId)return toast('Enter a Task ID','error');try{const r=await api(`/api/maintenance/requests/${encodeURIComponent(taskId)}`);$('#track-result').innerHTML=renderTaskDetail(r);}catch(e){$('#track-result').innerHTML=`<div class="empty danger-text">${escapeHtml(e.message)}</div>`;}}
function renderTaskDetail(r){const done=['SUBMITTED','PENDING_APPROVAL','APPROVED'].includes(r.status);const steps=['SUBMITTED','RECOMMENDED','PENDING_APPROVAL','APPROVED','REJECTED'];return `<div style="margin-top:22px"><div class="detail-grid"><div class="detail"><small>Task ID</small><strong>${escapeHtml(r.request_id)}</strong></div><div class="detail"><small>Status</small><strong>${escapeHtml(r.status)}</strong></div><div class="detail"><small>Department</small><strong>${escapeHtml(r.department)}</strong></div><div class="detail"><small>Section</small><strong>${escapeHtml(r.section_id)}</strong></div></div><div class="status-track">${steps.map((s,i)=>{let on=r.status===s||(['APPROVED'].includes(r.status)&&s!=='REJECTED'&&i<3)||(['PENDING_APPROVAL','RECOMMENDED'].includes(r.status)&&i<2);return `<div class="step ${on?'done':''}">${s.replaceAll('_',' ')}</div>`}).join('')}</div><div class="detail-grid"><div class="detail"><small>Work</small><strong>${escapeHtml(r.work_description)}</strong></div><div class="detail"><small>Asset</small><strong>${escapeHtml(r.asset_id)} · ${escapeHtml(r.asset_type)}</strong></div><div class="detail"><small>Priority inputs</small><strong>${escapeHtml(r.defect_severity)} / ${escapeHtml(r.failure_risk)} / safety=${escapeHtml(r.safety_related)}</strong></div><div class="detail"><small>Requested window</small><strong>${escapeHtml(r.preferred_date||'Any date')} ${escapeHtml(r.preferred_start_time||'')} ${r.preferred_end_time?`→ ${escapeHtml(r.preferred_end_time)}`:''}</strong></div></div>${r.rejection_reason?`<div class="validation-box"><div class="danger-text">Rejection reason: ${escapeHtml(r.rejection_reason)}</div></div>`:''}${r.block_id?`<div class="form-actions"><button class="secondary" onclick="openBlock('${escapeHtml(r.block_id)}')">Open assigned block</button></div>`:''}</div>`;}

async function renderCOA(){const d=await api('/api/coa/uploads');main.innerHTML=`<section class="panel"><div class="section-title"><h3>COA train schedule</h3><span>Upload and review schedules</span></div><div class="upload-zone"><div class="eyebrow">TRAIN OPERATIONS</div><h3 style="margin:8px 0">Upload COA schedule</h3><p class="muted">Rows are validated against section master, time format, dates and duplicate Train IDs.</p><label for="coa-file">Choose CSV / XLSX</label><input id="coa-file" type="file" accept=".csv,.xlsx,.xlsm" /><div class="upload-info" id="coa-file-name">No file selected</div><div class="form-actions"><a class="secondary" href="/api/templates/coa" target=<button class="secondary" type="button" onclick="downloadCOATemplate()">Download template</button>"_blank">Download template</a><button class="primary" onclick="uploadCOA()">Validate & upload</button></div></div><div id="coa-result"></div><div class="section-title" style="margin-top:28px"><h3>Uploaded schedules</h3><span>Most recent first</span></div><div class="request-list">${(d.uploads||[]).map(x=>`<div class="block-card"><div><div class="block-top"><span class="pill">${escapeHtml(x.planning_date)}</span><span class="pill">${x.row_count} trains</span></div><div class="block-meta">${escapeHtml(x.filename)} · uploaded by ${escapeHtml(x.uploaded_by)}</div></div></div>`).join('')||'<div class="empty">No uploads yet.</div>'}</div></section>`;$('#coa-file').onchange=()=>$('#coa-file-name').textContent=$('#coa-file').files[0]?.name||'No file selected';}
async function uploadCOA(){const file=$('#coa-file').files[0];if(!file)return toast('Select a COA file first','error');const fd=new FormData();fd.append('file',file);try{const r=await api('/api/coa/upload',{method:'POST',body:fd});$('#coa-result').innerHTML=`<div class="validation-box"><div class="success-text">✓ ${r.saved} train rows accepted for ${escapeHtml((r.planning_dates||[]).join(', '))}.</div></div>`;toast('COA schedule accepted','success');await renderCOA();}catch(e){showValidation(e.data||{errors:[e.message]},'coa-result');}}

async function renderBlocks(){const r=await api(`/api/blocks?planning_date=${state.planningDate}`);state.blocks=r.blocks||[];const title=state.user.department==='TDMS'?'Recommended blocks':'Blocks';main.innerHTML=`<section class="panel"><div class="section-title"><h3>${title}</h3><span>Sorted by urgency · ${state.planningDate}</span></div>${renderBlockCards(state.blocks,state.user.department==='BDMS')}</section><section class="panel" style="margin-top:16px"><div class="section-title"><h3>Schedule timeline</h3><span>Section-wise approved/recommended blocks</span></div>${renderTimeline(state.blocks)}</section>`;}
function renderTimeline(blocks){if(!blocks.length)return '<div class="empty">No schedule data.</div>';const sections=[...new Set(blocks.map(b=>b.section_id))].sort();const head=['','00','02','04','06','08','10','12','14','16','18','20','22'];let html='<div class="timeline"><div class="timeline-grid">'+head.map((h,i)=>`<div class="timeline-head ${i===0?'timeline-label':''}">${h}</div>`).join('');for(const s of sections){const bs=blocks.filter(b=>b.section_id===s);html+=`<div class="timeline-label">${escapeHtml(s)}</div><div class="bar-wrap">${bs.map(b=>{const start=mins(b.start_time),end=mins(b.end_time);const left=Math.max(0,start/1440*100);const width=Math.max(1,(end-start)/1440*100);return `<div class="bar ${b.coordination?'coordinated':''} ${b.status==='APPROVED'?'approved':''}" style="left:${left}%;width:${width}%" title="${escapeHtml(b.block_id)}">${escapeHtml(b.block_id)} · ${escapeHtml(b.priority)}</div>`}).join('')}</div>`;}html+='</div></div>';return html;}
function mins(t){const [h,m]=t.split(':').map(Number);return h*60+m;}

async function renderApprovals(){const r=await api(`/api/blocks?planning_date=${state.planningDate}&status=PENDING_APPROVAL`);main.innerHTML=`<section class="panel"><div class="section-title"><h3>Pending BDMS approvals</h3><span>${r.blocks.length} block(s)</span></div>${renderBlockCards(r.blocks,true)}</section>`;}
async function openBlock(id){try{const b=await api(`/api/blocks/${encodeURIComponent(id)}`);openModal(renderBlockModal(b));}catch(e){toast(e.message,'error');}}
function renderBlockModal(b){return `<div class="modal-head"><div><div class="eyebrow">${escapeHtml(b.status)}</div><h3>${escapeHtml(b.block_id)}</h3><div class="muted">${escapeHtml(b.section_id)} · ${escapeHtml(b.planning_date)} · ${escapeHtml(b.start_time)} → ${escapeHtml(b.end_time)}</div></div><button class="close-btn" onclick="closeModal()">✕</button></div><div class="detail-grid" style="margin-top:18px"><div class="detail"><small>Priority</small><strong>${escapeHtml(b.priority)} · score ${Number(b.priority_score).toFixed(0)}</strong></div><div class="detail"><small>Coordination</small><strong>${b.coordination?'Multiple departments coordinated':'Single maintenance task(s)'}</strong></div><div class="detail"><small>Existing block</small><strong>${b.existing_block?'Yes · '+escapeHtml(b.block_calendar_id||''):'No existing block matched'}</strong></div><div class="detail"><small>Duration</small><strong>${b.duration_minutes} minutes</strong></div></div><div class="section-title" style="margin-top:24px"><h3>Maintenance tasks in this block</h3><span>${b.tasks.length} task(s)</span></div><div class="request-list">${b.tasks.map(t=>`<div class="panel"><div class="block-top"><span class="pill ${priorityClass(t.priority)}">${escapeHtml(t.priority)}</span><span class="pill">${escapeHtml(t.department)}</span><span class="pill">${escapeHtml(t.task_id)}</span></div><div class="detail-grid" style="margin-top:10px"><div class="detail"><small>Location</small><strong>${escapeHtml(t.location)}</strong></div><div class="detail"><small>Asset</small><strong>${escapeHtml(t.asset_id)} · ${escapeHtml(t.asset_type)}</strong></div><div class="detail"><small>Work</small><strong>${escapeHtml(t.work_description)}</strong></div><div class="detail"><small>Resources</small><strong>${escapeHtml(t.required_resources)}</strong></div><div class="detail"><small>Defect / risk</small><strong>${escapeHtml(t.defect_severity)} / ${escapeHtml(t.failure_risk)}</strong></div><div class="detail"><small>Operational status</small><strong>${escapeHtml(t.asset_operational_status)}</strong></div></div></div>`).join('')}</div>${state.user.department==='BDMS'&&b.status==='PENDING_APPROVAL'?`<div class="form-actions"><button class="secondary" onclick="openModify('${escapeHtml(b.block_id)}')">Modify</button><button class="danger-button" onclick="rejectBlock('${escapeHtml(b.block_id)}')">Reject</button><button class="primary" onclick="approveBlock('${escapeHtml(b.block_id)}')">Approve block</button></div>`:''}`;}

async function openModify(id){try{const r=await api(`/api/blocks/${encodeURIComponent(id)}/slots`);openModal(renderModifyModal(r));}catch(e){toast(e.message,'error');}}
function renderModifyModal(r){return `<div class="modal-head"><div><div class="eyebrow">MANUAL MODIFICATION</div><h3>${escapeHtml(r.block.block_id)}</h3><div class="muted">Current ${escapeHtml(r.block.start_time)} → ${escapeHtml(r.block.end_time)} · ${r.block.duration_minutes} min</div></div><button class="close-btn" onclick="closeModal()">✕</button></div><div class="validation-box"><div><strong>Select a feasible alternative slot</strong></div>${r.constraints.map(c=>`<div class="muted" style="margin-top:5px">• ${escapeHtml(c)}</div>`).join('')}</div><div class="slot-list">${(r.available_slots||[]).map(s=>`<div class="slot-option"><div><div class="slot-time">${escapeHtml(s.start_time)} → ${escapeHtml(s.end_time)}</div><div class="slot-meta">${escapeHtml(s.suitability)}</div></div><button class="small-btn" onclick="applyModify('${escapeHtml(r.block.block_id)}','${escapeHtml(s.start_time)}','${escapeHtml(s.end_time)}')">Select</button></div>`).join('')||'<div class="empty">No alternative feasible slots are available.</div>'}</div>`;}
async function applyModify(id,start,end){const reason=prompt('Modification reason (optional):','BDMS manual adjustment');try{await api(`/api/blocks/${encodeURIComponent(id)}/modify`,{method:'POST',body:JSON.stringify({start_time:start,end_time:end,reason:reason||''})});toast('Block modified and returned to pending approval','success');closeModal();renderPage();}catch(e){toast(e.message,'error');}}
async function approveBlock(id){try{await api(`/api/blocks/${encodeURIComponent(id)}/approve`,{method:'POST'});toast('Block approved and all departments notified','success');closeModal();renderPage();refreshNotifications();}catch(e){toast(e.message,'error');}}
async function rejectBlock(id){const reason=prompt('Reason for rejection:','Block requires further review');if(!reason)return;try{await api(`/api/blocks/${encodeURIComponent(id)}/reject`,{method:'POST',body:JSON.stringify({reason})});toast('Block rejected','success');closeModal();renderPage();}catch(e){toast(e.message,'error');}}

async function renderNotifications(){const r=await api('/api/notifications');main.innerHTML=`<section class="panel"><div class="section-title"><h3>Alerts</h3><span>Department notifications</span></div><div class="notif-list">${(r.notifications||[]).map(n=>`<div class="notification ${n.is_read?'':'unread'}"><div class="block-top"><span class="pill">${escapeHtml(n.title)}</span>${!n.is_read?'<span class="pill high">NEW</span>':''}</div><div style="margin-top:8px;color:#c9d7e4;font-size:13px;line-height:1.5">${escapeHtml(n.message)}</div><div class="block-meta" style="margin-top:8px">${escapeHtml(n.created_at)}</div>${!n.is_read?`<div class="form-actions"><button class="small-btn" onclick="markRead(${n.id})">Mark read</button></div>`:''}</div>`).join('')||'<div class="empty">No alerts.</div>'}</div></section>`;}
async function refreshNotifications(){try{const r=await api('/api/notifications');const unread=(r.notifications||[]).filter(n=>!n.is_read).length;const c=$('#notify-count');c.textContent=unread;c.style.display=unread?'inline-block':'none';}catch{}}
async function markRead(id){await api(`/api/notifications/${id}/read`,{method:'POST'});renderPage();refreshNotifications();}
$('#notify-button').onclick=()=>go('notifications'); $('#refresh-button').onclick=()=>renderPage(); $('#planning-date').onchange=(e)=>{state.planningDate=e.target.value;localStorage.setItem('vx_date',state.planningDate);renderPage();}; $('#logout-button').onclick=()=>logout(true);
async function generatePlan(){try{const r=await api('/api/planning/generate',{method:'POST',body:JSON.stringify({planning_date:state.planningDate})});toast(`${r.blocks_created||0} recommended blocks generated`,'success');go(state.user.department==='TDMS'?'blocks':state.user.department==='BDMS'?'approvals':'dashboard');}catch(e){toast(e.message,'error');}}
function openModal(html){$('#modal-root').innerHTML=`<div class="modal-backdrop"><div class="modal">${html}</div></div>`;$('#modal-root').querySelector('.modal-backdrop').onclick=e=>{if(e.target.classList.contains('modal-backdrop'))closeModal();};}

function closeModal(){$('#modal-root').innerHTML='';}

async function downloadMaintenanceTemplate() {
  try {
    const response = await fetch('/api/templates/maintenance', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${state.token}`
      }
    });

    if (response.status === 401) {
      logout(false);
      throw new Error('Session expired. Please sign in again.');
    }

    if (!response.ok) {
      let message = 'Unable to download template';
      try {
        const data = await response.json();
        message = data.detail || message;
      } catch {}
      throw new Error(message);
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = 'maintenance_template.xlsx';
    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
    toast('Maintenance template downloaded', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function downloadCOATemplate() {
  try {
    const response = await fetch('/api/templates/coa', {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${state.token}`
      }
    });

    if (response.status === 401) {
      logout(false);
      throw new Error('Session expired. Please sign in again.');
    }

    if (!response.ok) {
      let message = 'Unable to download COA template';
      try {
        const data = await response.json();
        message = data.detail || message;
      } catch {}
      throw new Error(message);
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = 'coa_template.xlsx';
    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
    toast('COA template downloaded', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

$('#login-form').onsubmit=async(e)=>{e.preventDefault();try{const r=await api('/api/auth/login',{method:'POST',body:JSON.stringify({department:$('#login-department').value,user_id:$('#login-user').value,password:$('#login-password').value})});state.token=r.token;state.user=r.user;localStorage.setItem('vx_token',r.token);localStorage.setItem('vx_user',JSON.stringify(r.user));toast('Signed in','success');showApp();}catch(err){toast(err.message,'error');}};
if(state.token&&state.user){api('/api/me').then(showApp).catch(()=>showLogin());}else showLogin();
window.go=go;window.trackTask=trackTask;window.openBlock=openBlock;window.openModify=openModify;window.applyModify=applyModify;window.approveBlock=approveBlock;window.rejectBlock=rejectBlock;window.markRead=markRead;window.generatePlan=generatePlan;window.closeModal=closeModal;window.uploadMaintenance=uploadMaintenance;window.uploadCOA=uploadCOA;window.mins=mins;

async function loadDemo(){try{const r=await api('/api/demo/load',{method:'POST'});toast(`${r.maintenance_requests} demo requests ready`,'success');}catch(e){toast(e.message,'error');}}
window.loadDemo=loadDemo;

window.downloadMaintenanceTemplate = downloadMaintenanceTemplate;

window.downloadCOATemplate = downloadCOATemplate;