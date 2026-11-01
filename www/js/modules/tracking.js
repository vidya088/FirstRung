// www/js/modules/tracking.js — Verification & Tracking module
// CSS: www/css/tracking.css (prefix "trk-")
//
// >>> ADJUST THESE IMPORTS to match the starter kit (paths/names only) <<<
import { db } from '../firebase.js';
import { guard } from '../guard.js';
import { oppCard } from '../components/oppCard.js';
import { APP_STATUSES } from '../constants.js';
// <<<
import {
  doc, getDoc, getDocs, setDoc, updateDoc, deleteDoc, writeBatch, collection,
  arrayUnion, arrayRemove
} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js';

// ASSUMED DATA MODEL
//  opportunities/{id}: title, organisation, deadline (Timestamp|ISO), status ('pending'|'live'|'rejected'|'expired')
//  saved/{uid}: { ids: [] }
//  applications/{uid}/items/{oppId}: { oppId, status, appliedDate, title, organisation, deadline }
//  user = { uid, role } | null ; role = 'student' | 'provider' | 'admin'

const DAY_MS = 24 * 60 * 60 * 1000;

/* ===================== helpers ===================== */

function toDate(v) {
  if (!v) return null;
  if (typeof v.toDate === 'function') return v.toDate();
  const d = new Date(v);
  return isNaN(d) ? null : d;
}

function isExpired(opp) {
  if (opp.status === 'expired') return true;
  const d = toDate(opp.deadline);
  if (!d) return false;
  const end = new Date(d);
  end.setHours(23, 59, 59, 999);
  return end < new Date();
}

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function fmtDate(v) {
  const d = toDate(v);
  return d ? d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
}

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text; // textContent = no HTML injection
  return n;
}

function btn(label, cls, onClick) {
  const b = el('button', `trk-btn ${cls}`, label);
  b.type = 'button';
  if (onClick) b.addEventListener('click', onClick);
  return b;
}

// oppCard may return an Element or an HTML string; handle both.
function cardNode(opp) {
  const out = oppCard(opp);
  if (out instanceof Node) return out;
  const t = document.createElement('template');
  t.innerHTML = String(out).trim();
  return t.content.firstElementChild || el('div');
}

async function getSavedIds(uid) {
  const s = await getDoc(doc(db, 'saved', uid));
  return s.exists() ? (s.data().ids || []) : [];
}

async function getAppliedIds(uid) {
  const s = await getDocs(collection(db, 'applications', uid, 'items'));
  return s.docs.map(d => d.id);
}

/* ===================== STEP 1: hooks ===================== */

export async function mountOppActions(container, opp, user) {
  container.innerHTML = '';
  const wrap = el('div', 'trk-actions');
  container.appendChild(wrap);

  if (!user) {
    const a = el('a', 'trk-login-prompt', 'Log in to save or apply');
    a.href = '#/login';
    wrap.appendChild(a);
    return;
  }
  if (user.role !== 'student') return;

  const expired = isExpired(opp);
  let saved = false, applied = false;

  try {
    const [ids, appSnap] = await Promise.all([
      getSavedIds(user.uid),
      getDoc(doc(db, 'applications', user.uid, 'items', opp.id))
    ]);
    saved = ids.includes(opp.id);
    applied = appSnap.exists();
  } catch (err) {
    console.error('[tracking] load state failed', err);
    wrap.appendChild(el('span', 'trk-error', 'Could not load actions. Try again.'));
    return;
  }

  const saveBtn = btn('', 'trk-btn--secondary');
  const applyBtn = btn('', 'trk-btn--primary');
  const msg = el('span', 'trk-error');
  msg.setAttribute('role', 'status');

  function paint() {
    saveBtn.textContent = saved ? 'Unsave' : 'Save';
    saveBtn.setAttribute('aria-pressed', String(saved));
    if (applied) { applyBtn.textContent = 'Applied ✓'; applyBtn.disabled = true; }
    else if (expired) { applyBtn.textContent = 'Expired'; applyBtn.disabled = true; applyBtn.title = 'This listing has expired'; }
    else { applyBtn.textContent = 'Apply'; applyBtn.disabled = false; }
  }

  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true; msg.textContent = '';
    try {
      await setDoc(doc(db, 'saved', user.uid),
        { ids: saved ? arrayRemove(opp.id) : arrayUnion(opp.id) }, { merge: true });
      saved = !saved;
    } catch (err) {
      console.error('[tracking] save failed', err);
      msg.textContent = 'Could not update saved list.';
    }
    saveBtn.disabled = false; paint();
  });

  applyBtn.addEventListener('click', async () => {
    if (applied || expired) return;
    applyBtn.disabled = true; msg.textContent = '';
    try {
      await setDoc(doc(db, 'applications', user.uid, 'items', opp.id), {
        oppId: opp.id, status: 'Applied', appliedDate: todayISO(),
        title: opp.title || '', organisation: opp.organisation || '',
        deadline: opp.deadline || null
      });
      applied = true;
    } catch (err) {
      console.error('[tracking] apply failed', err);
      msg.textContent = 'Could not record application.';
    }
    paint();
  });

  paint();
  wrap.append(saveBtn, applyBtn, msg);
}

export async function getDeadlineReminders(user) {
  if (!user || user.role !== 'student') return [];
  try {
    const [savedIds, appliedIds] = await Promise.all([getSavedIds(user.uid), getAppliedIds(user.uid)]);
    const applied = new Set(appliedIds);
    const snaps = await Promise.all(
      savedIds.filter(id => !applied.has(id)).map(id => getDoc(doc(db, 'opportunities', id)))
    );
    const now = Date.now();
    return snaps
      .filter(s => s.exists())
      .map(s => ({ id: s.id, ...s.data() }))
      .filter(o => {
        if (o.status !== 'live' || isExpired(o)) return false;
        const d = toDate(o.deadline);
        return d && d.getTime() - now <= 7 * DAY_MS;
      })
      .sort((a, b) => toDate(a.deadline) - toDate(b.deadline));
  } catch (err) {
    console.error('[tracking] reminders failed', err);
    return [];
  }
}

/* ===================== STEP 2: /saved ===================== */

export async function renderSaved(container, user) {
  if (!guard(container, user, ['student'])) return;
  container.innerHTML = '';
  const page = el('section', 'trk-page');
  page.appendChild(el('h2', 'trk-title', 'Saved listings'));
  container.appendChild(page);

  const remindersBox = el('div', 'trk-reminders');
  const grid = el('div', 'trk-grid');
  const status = el('p', 'trk-muted', 'Loading…');
  page.append(remindersBox, status, grid);

  async function load() {
    grid.innerHTML = ''; remindersBox.innerHTML = '';
    try {
      const [ids, reminders] = await Promise.all([getSavedIds(user.uid), getDeadlineReminders(user)]);

      if (reminders.length) {
        remindersBox.appendChild(el('h3', 'trk-subtitle', '⏰ Closing within 7 days'));
        const ul = el('ul', 'trk-reminder-list');
        reminders.forEach(o => {
          ul.appendChild(el('li', '', `${o.title} — ${o.organisation || ''} (closes ${fmtDate(o.deadline)})`));
        });
        remindersBox.appendChild(ul);
      }

      const snaps = await Promise.all(ids.map(id => getDoc(doc(db, 'opportunities', id))));
      const opps = snaps.filter(s => s.exists()).map(s => ({ id: s.id, ...s.data() }));

      status.textContent = opps.length ? '' : 'You have not saved any listings yet.';
      opps.forEach(o => {
        const cell = el('div', 'trk-cell');
        cell.appendChild(cardNode(o));
        if (isExpired(o)) cell.appendChild(el('span', 'trk-badge trk-badge--expired', 'Expired'));
        cell.appendChild(btn('Remove from saved', 'trk-btn--danger', async () => {
          if (!confirm(`Remove "${o.title}" from your saved list?`)) return;
          try {
            await setDoc(doc(db, 'saved', user.uid), { ids: arrayRemove(o.id) }, { merge: true });
            load();
          } catch (err) {
            console.error('[tracking] remove saved failed', err);
            alert('Could not remove. Try again.');
          }
        }));
        grid.appendChild(cell);
      });
    } catch (err) {
      console.error('[tracking] load saved failed', err);
      status.textContent = 'Could not load saved listings.';
    }
  }
  load();
}

/* ===================== STEP 3: /applications ===================== */

export async function renderApplications(container, user) {
  if (!guard(container, user, ['student'])) return;
  container.innerHTML = '';
  const page = el('section', 'trk-page');
  page.appendChild(el('h2', 'trk-title', 'My applications'));
  const status = el('p', 'trk-muted', 'Loading…');
  const scroll = el('div', 'trk-table-wrap');
  page.append(status, scroll);
  container.appendChild(page);

  try {
    const snap = await getDocs(collection(db, 'applications', user.uid, 'items'));
    const rows = snap.docs.map(d => ({ id: d.id, ...d.data() }));
    if (!rows.length) { status.textContent = 'You have not applied to anything yet.'; return; }
    status.textContent = '';

    const table = el('table', 'trk-table');
    const head = el('tr');
    ['Listing', 'Organisation', 'Applied on', 'Deadline', 'Status'].forEach(h => head.appendChild(el('th', '', h)));
    table.appendChild(el('thead')).appendChild(head);

    const tbody = el('tbody');
    rows.forEach(r => {
      const tr = el('tr');
      tr.append(
        el('td', '', r.title || r.id),
        el('td', '', r.organisation || '—'),
        el('td', '', fmtDate(r.appliedDate)),
        el('td', '', fmtDate(r.deadline))
      );
      const select = el('select', 'trk-select');
      select.setAttribute('aria-label', `Status for ${r.title || r.id}`);
      APP_STATUSES.forEach(s => {
        const o = el('option', '', s); o.value = s; if (s === r.status) o.selected = true;
        select.appendChild(o);
      });
      select.addEventListener('change', async () => {
        const prev = r.status;
        select.disabled = true;
        try {
          await updateDoc(doc(db, 'applications', user.uid, 'items', r.id), { status: select.value });
          r.status = select.value;
        } catch (err) {
          console.error('[tracking] status update failed', err);
          select.value = prev;
          alert('Could not update status. Try again.');
        }
        select.disabled = false;
      });
      tr.appendChild(el('td')).appendChild(select);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    scroll.appendChild(table);
  } catch (err) {
    console.error('[tracking] load applications failed', err);
    status.textContent = 'Could not load applications.';
  }
}

/* ===================== STEP 4: /admin ===================== */

export async function renderAdmin(container, user) {
  if (!guard(container, user, ['admin'])) return; // Firestore rules enforce this again server-side
  container.innerHTML = '';
  const page = el('section', 'trk-page');
  page.appendChild(el('h2', 'trk-title', 'Admin review'));
  const body = el('div');
  page.appendChild(body);
  container.appendChild(page);

  async function load() {
    body.innerHTML = '';
    let all;
    try {
      const snap = await getDocs(collection(db, 'opportunities'));
      all = snap.docs.map(d => ({ id: d.id, ...d.data() }));
    } catch (err) {
      console.error('[tracking] admin load failed', err);
      body.appendChild(el('p', 'trk-error', 'Could not load listings.'));
      return;
    }

    const pending = all.filter(o => o.status === 'pending');
    const expired = all.filter(o => o.status !== 'pending' && o.status !== 'rejected' && isExpired(o));
    const live = all.filter(o => o.status === 'live' && !isExpired(o));

    const counts = el('div', 'trk-counts');
    [['Pending', pending.length], ['Live', live.length], ['Expired', expired.length]].forEach(([k, v]) => {
      const c = el('div', 'trk-count');
      c.append(el('span', 'trk-count-num', String(v)), el('span', 'trk-count-label', k));
      counts.appendChild(c);
    });
    body.appendChild(counts);

    async function run(fn, errMsg) {
      try { await fn(); await load(); }
      catch (err) { console.error('[tracking] admin action failed', err); alert(errMsg); }
    }

    function section(title, list, buildActions) {
      const s = el('div', 'trk-section');
      s.appendChild(el('h3', 'trk-subtitle', `${title} (${list.length})`));
      if (!list.length) s.appendChild(el('p', 'trk-muted', 'Nothing here.'));
      list.forEach(o => {
        const row = el('div', 'trk-row');
        const info = el('div', 'trk-row-info');
        info.append(
          el('strong', '', o.title || o.id),
          el('span', 'trk-muted', `${o.organisation || '—'} · closes ${fmtDate(o.deadline)}`)
        );
        const actions = el('div', 'trk-row-actions');
        buildActions(o).forEach(b => actions.appendChild(b));
        row.append(info, actions);
        s.appendChild(row);
      });
      return s;
    }

    body.appendChild(section('Pending', pending, o => [
      btn('Approve', 'trk-btn--primary', () => {
        if (!confirm(`Approve "${o.title}" and make it live?`)) return;
        run(() => updateDoc(doc(db, 'opportunities', o.id), { status: 'live' }), 'Could not approve.');
      }),
      btn('Reject', 'trk-btn--danger', () => {
        if (!confirm(`Reject "${o.title}"?`)) return;
        run(() => updateDoc(doc(db, 'opportunities', o.id), { status: 'rejected' }), 'Could not reject.');
      })
    ]));

    const expSec = section('Expired', expired, o => [
      btn('Remove', 'trk-btn--danger', () => {
        if (!confirm(`Permanently remove "${o.title}"?`)) return;
        run(() => deleteDoc(doc(db, 'opportunities', o.id)), 'Could not remove.');
      })
    ]);
    if (expired.length) {
      const removeAll = btn('Remove all expired', 'trk-btn--danger', () => {
        if (!confirm(`Permanently remove ALL ${expired.length} expired listings? This cannot be undone.`)) return;
        run(async () => {
          for (let i = 0; i < expired.length; i += 400) { // batch limit is 500
            const batch = writeBatch(db);
            expired.slice(i, i + 400).forEach(o => batch.delete(doc(db, 'opportunities', o.id)));
            await batch.commit();
          }
        }, 'Could not remove all expired.');
      });
      expSec.insertBefore(removeAll, expSec.children[1] || null);
    }
    body.appendChild(expSec);

    body.appendChild(section('Live', live, o => [
      btn('Remove (suspicious)', 'trk-btn--danger', () => {
        if (!confirm(`Remove "${o.title}" as suspicious? It will be deleted.`)) return;
        run(() => deleteDoc(doc(db, 'opportunities', o.id)), 'Could not remove.');
      })
    ]));
  }
  load();
}