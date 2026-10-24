(() => {
  // Sample data. Replace with API calls to the FastAPI backend.
  const U = [
    { t: 'Update rule and learning rate', type: 'Procedure', book: 'Optimization basics, ch. 4', a: ['p37.2', 'p38.1'],
      g: { r: [2, 2], p: [3, 3], t: [0, 1], c: 'ok', au: [1, 3] }, s: ['hit','hit','shaky','hit','hit','due','','','','','',''] },
    { t: 'Why a learning rate that is too large diverges', type: 'Concept', book: 'Optimization basics, ch. 4', a: ['p39.3'],
      g: { r: [1, 2], p: [1, 3], t: [0, 1], c: 'high', au: null }, s: ['miss','shaky','hit','shaky','due','','','','','','',''] },
    { t: 'Batch, stochastic and mini-batch compared', type: 'Concept', book: 'Optimization basics, ch. 4', a: ['p41.1', 'p41.4'],
      g: { r: [0, 2], p: [0, 3], t: [0, 1], c: 'none', au: null }, s: ['miss','due','','','','','','','','','',''] },
    { t: 'Implement gradient descent for linear regression', type: 'Skill', book: 'Optimization basics, ch. 4', a: ['p44.2'],
      g: { r: [1, 2], p: [2, 3], t: [0, 1], c: 'none', au: [0, 3] }, s: ['hit','shaky','due','','','','','','','','',''] }
  ];
  const I = [
    { unit: 'Update rule and learning rate', a: 'p37.2',
      q: 'Explain the gradient descent update rule and what each part controls.',
      src: 'Each step moves the parameters against the gradient of the loss. The learning rate scales how far one step travels, so the new parameters are the current parameters minus the learning rate times the gradient. Where the gradient is zero, the update leaves the parameters unchanged.',
      pts: ['Moves against the gradient', 'Learning rate scales the step size', 'Zero gradient means no change'] },
    { unit: 'Why a learning rate that is too large diverges', a: 'p39.3',
      q: 'What happens to training when the learning rate is far too large?',
      src: 'A step that is too long overshoots the minimum and can land at a higher loss than before. Repeated overshoots make the loss oscillate or grow instead of falling.',
      pts: ['Steps overshoot the minimum', 'Loss oscillates or rises'] },
    { unit: 'Batch, stochastic and mini-batch compared', a: 'p41.1',
      q: 'When would you choose mini-batch gradient descent over full-batch?',
      src: 'Full-batch updates use every example and give smooth but slow steps. Mini-batches accept some noise in the gradient in return for many more updates per pass, and they fit in memory.',
      pts: ['Many more updates per pass', 'Fits in memory', 'Gradient is noisier'] }
  ];

  const main = document.querySelector('#view');
  const tags = a => a.map(x => `<span class="tag">${x}</span>`).join('');
  const strip = a => `<span class="strip" role="img" aria-label="Review history, oldest first">${a.map(v => `<i class="${v}" title="${v || 'upcoming'}"></i>`).join('')}</span>`;
  const dots = ([d, n]) => `<span class="dots" aria-label="${d} of ${n}">${'●'.repeat(d)}${'○'.repeat(n - d)}</span>`;
  const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' });

  function nextStep(u) {
    const g = u.g;
    if (g.r[0] < g.r[1]) return `Explain it again, at least 7 days after the last time (${g.r[0]} of ${g.r[1]} done)`;
    if (g.p[0] < g.p[1]) return `Solve ${g.p[1] - g.p[0]} more varied problems without hints`;
    if (g.t[0] < g.t[1]) return 'Do one cold task where the method is not named';
    if (g.c === 'high') return 'Rate confidence honestly on the next review';
    if (g.au && g.au[0] < g.au[1]) return `Redo it from a blank file on ${g.au[1] - g.au[0]} more days`;
    return 'All gates have evidence';
  }

  /* ---------- Today ---------- */
  function viewToday() {
    return `<h1>Close the book. Say what you remember.</h1>
      <p class="lede">${today}. ${I.length} items are due, about 20 minutes. Reviews come first because they fade on a clock. New material waits until the queue is clear.</p>
      <a class="btn" href="#retrieve">Start ${I.length} reviews</a>
      <h2>On the desk</h2>
      <ul class="desk">${U.map(u => `<li><div><b>${u.t}</b><div class="meta">${u.type}, ${u.book}</div><div>${tags(u.a)}</div></div>${strip(u.s)}</li>`).join('')}</ul>
      <div class="key" aria-label="Legend">
        <span><span class="strip"><i class="hit"></i></span>Recalled</span>
        <span><span class="strip"><i class="shaky"></i></span>Shaky</span>
        <span><span class="strip"><i class="miss"></i></span>Missed</span>
        <span><span class="strip"><i class="due"></i></span>Due next</span>
      </div>`;
  }

  /* ---------- Retrieve ---------- */
  let s;
  const reset = () => (s = { i: 0, step: 'recall', text: '', conf: 50, results: [], last: null });
  reset();
  const label = c => (c < 25 ? 'Guessing' : c < 55 ? 'Shaky' : c < 85 ? 'Fairly sure' : 'Certain');

  function viewRetrieve() {
    if (s.i >= I.length) return summary();
    const it = I[s.i];
    const head = `<p class="count">Item ${s.i + 1} of ${I.length}. ${it.unit}</p>`;
    if (s.step === 'recall') return `${head}<section class="slip"><h1>${it.q}</h1>
      <textarea id="ans" rows="5" aria-label="Your answer" placeholder="Write it from memory. The source is hidden.">${s.text}</textarea></section>
      <button class="btn" id="lock">Lock my answer</button>`;
    if (s.step === 'conf') return `${head}<section class="slip"><h1>${it.q}</h1>
      <label for="conf">How sure are you that your answer is right?</label>
      <input type="range" id="conf" min="0" max="100" step="10" value="${s.conf}"><output id="cl">${label(s.conf)}, ${s.conf} percent</output></section>
      <button class="btn" id="show">Show the source</button>`;
    if (s.step === 'reveal') return `${head}<div class="cols">
      <section class="slip"><h2>What you wrote</h2><p>${s.text.trim() ? s.text.replace(/</g, '&lt;') : '<i>Nothing written.</i>'}</p></section>
      <section class="slip src"><h2>What the source says</h2><p>${tags([it.a])}<br>${it.src}</p></section></div>
      <h2 style="margin-top:0">Which points did you have?</h2>
      <ul class="pts">${it.pts.map((p, k) => `<li><label><input type="checkbox" data-k="${k}">${p}</label></li>`).join('')}</ul>
      <button class="btn" id="rec">Record result</button>`;
    const r = s.last;
    return `${head}<div class="stamp ${r.o}">${r.o === 'hit' ? 'Recalled' : r.o === 'shaky' ? 'Shaky' : 'Missed'}</div>
      <p class="lede">You were ${r.conf} percent sure and covered ${r.got} of ${it.pts.length} points.${r.conf >= 70 && r.o !== 'hit' ? ' That is overconfidence, and it is the useful thing to notice.' : ''} This adds a mark to the ledger.</p>
      <button class="btn" id="next">${s.i + 1 < I.length ? 'Next item' : 'Finish'}</button>`;
  }

  function summary() {
    const n = s.results.length, acc = s.results.reduce((a, r) => a + r.score, 0) / n * 100;
    const conf = s.results.reduce((a, r) => a + r.conf, 0) / n;
    const gap = Math.round(conf - acc);
    const note = gap > 15 ? 'You felt surer than the results justify. Trust the schedule over the feeling.' : gap < -15 ? 'You knew more than you thought. Shorter intervals are not needed here.' : 'Your confidence matched your results well.';
    return `<h1>Queue cleared.</h1>
      <p class="lede">Average confidence was ${Math.round(conf)} percent. Actual coverage was ${Math.round(acc)} percent. ${note}</p>
      <a class="btn" href="#today">Back to today</a> <a class="btn ghost" href="#ledger">See the ledger</a>`;
  }

  function bindRetrieve() {
    const $ = id => document.getElementById(id), rr = () => { main.innerHTML = viewRetrieve(); bindRetrieve(); };
    if ($('ans')) { $('ans').focus(); $('lock').onclick = () => { s.text = $('ans').value; s.step = 'conf'; rr(); }; }
    if ($('conf')) $('conf').oninput = e => { s.conf = +e.target.value; $('cl').textContent = `${label(s.conf)}, ${s.conf} percent`; };
    if ($('show')) $('show').onclick = () => { s.step = 'reveal'; rr(); };
    if ($('rec')) $('rec').onclick = () => {
      const it = I[s.i], got = main.querySelectorAll('.pts input:checked').length, score = got / it.pts.length;
      const o = score >= 0.8 ? 'hit' : score >= 0.4 ? 'shaky' : 'miss';
      s.last = { o, got, conf: s.conf, score }; s.results.push(s.last); s.step = 'result'; rr();
    };
    if ($('next')) $('next').onclick = () => { s.i++; s.step = 'recall'; s.text = ''; s.conf = 50; rr(); };
  }

  /* ---------- Ledger ---------- */
  function viewLedger() {
    const conf = c => (c === 'ok' ? '<span class="good">Calibrated</span>' : c === 'high' ? '<span class="bad">Overconfident</span>' : 'Not enough data');
    return `<h1>What you can show, not what you read.</h1>
      <p class="lede">A unit counts as mastered only when every gate has evidence. A quiz score alone never fills a gate.</p>
      <div class="wrap"><table><thead><tr><th>Unit</th><th>Delayed recall</th><th>Varied problems</th><th>Cold transfer</th><th>Confidence</th><th>Automatic</th><th>Next evidence</th></tr></thead>
      <tbody>${U.map(u => `<tr><td><b>${u.t}</b><div class="meta">${u.type}</div></td><td>${dots(u.g.r)}</td><td>${dots(u.g.p)}</td><td>${dots(u.g.t)}</td><td>${conf(u.g.c)}</td><td>${u.g.au ? dots(u.g.au) : 'Not needed'}</td><td class="next">${nextStep(u)}</td></tr>`).join('')}</tbody></table></div>`;
  }

  /* ---------- Router ---------- */
  const views = { today: viewToday, retrieve: viewRetrieve, ledger: viewLedger };
  function route() {
    const k = (location.hash || '#today').slice(1), v = views[k] ? k : 'today';
    if (v === 'retrieve' && s.i >= I.length) reset();
    document.querySelectorAll('.rail a').forEach(a => a.getAttribute('href') === '#' + v ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
    main.innerHTML = views[v]();
    if (v === 'retrieve') bindRetrieve();
    main.focus({ preventScroll: true }); scrollTo(0, 0);
  }
  addEventListener('hashchange', route);
  route();
})();
