/* The Week in Ink deck engine (shared by generated editions).
 *
 * Behaviour is a re-implementation of edition 28's inline engine against the same
 * DOM and the same class names, with one deliberate difference: EVERY lookup is
 * null-guarded. Edition 28's original engine assumes a podcast player, chapter
 * list and transcript exist, so reusing it verbatim on an edition without audio
 * throws on the first addEventListener. Generated editions have no episode, so
 * this engine treats every optional part as optional.
 *
 * Edition 28 keeps its own inline engine and does not load this file.
 *
 * Contract: .deck-viewport > .stage#stage > section.slide, plus optional
 * #prev #next #dots #curNum #totNum #edgeLeft #edgeRight #lightbox #lbImg #lbCap #lbClose.
 */
(function () {
  var body = document.body;
  body.classList.add('js');
  var stage = document.getElementById('stage');
  if (!stage) return;
  var slides = Array.prototype.slice.call(stage.querySelectorAll('.slide'));
  var total = slides.length;
  if (!total) return;
  var idx = 0;

  var $ = function (id) { return document.getElementById(id); };
  var prevBtn = $('prev'), nextBtn = $('next'), dotsWrap = $('dots');
  var curNum = $('curNum'), totNum = $('totNum');
  var edgeL = $('edgeLeft'), edgeR = $('edgeRight');

  // ---- scale the fixed 1280x720 stage into whatever viewport we get ----------
  function fit() {
    var navH = 76, pad = 26;
    var w = window.innerWidth - pad * 2;
    var h = window.innerHeight - navH - pad * 2;
    var s = Math.min(w / 1280, h / 720);
    if (!isFinite(s) || s <= 0) s = 1;
    stage.style.setProperty('--scale', s);
    var gutter = Math.max(0, (window.innerWidth - 1280 * s) / 2);
    if (edgeL) edgeL.style.width = gutter + 'px';
    if (edgeR) edgeR.style.width = gutter + 'px';
  }
  window.addEventListener('resize', fit);
  fit();

  // ---- dots -----------------------------------------------------------------
  var dotBtns = [];
  if (dotsWrap) {
    for (var i = 0; i < total; i++) {
      (function (n) {
        var b = document.createElement('button');
        b.setAttribute('role', 'tab');
        b.setAttribute('aria-label', 'Go to page ' + (n + 1));
        b.addEventListener('click', function () { go(n); });
        dotsWrap.appendChild(b);
        dotBtns.push(b);
      })(i);
    }
  }
  if (totNum) totNum.textContent = ('0' + total).slice(-2);

  function pad2(n) { return ('0' + n).slice(-2); }

  function render(dir) {
    stage.setAttribute('data-dir', dir || 'next');
    slides.forEach(function (s, i) { s.classList.toggle('is-active', i === idx); });
    dotBtns.forEach(function (d, i) { d.classList.toggle('on', i === idx); });
    if (curNum) curNum.textContent = pad2(idx + 1);
    var id = slides[idx].id;
    if (id && location.hash !== '#' + id) {
      history.replaceState(null, '', '#' + id);
    }
    if (prevBtn) prevBtn.disabled = false;
    if (nextBtn) nextBtn.disabled = false;
  }
  function go(n, dir) {
    n = Math.max(0, Math.min(total - 1, n));
    if (n === idx) return;
    var d = dir || (n > idx ? 'next' : 'prev');
    idx = n;
    render(d);
  }
  function next() { go(idx + 1, 'next'); }
  function prev() { go(idx - 1, 'prev'); }

  if (prevBtn) prevBtn.addEventListener('click', prev);
  if (nextBtn) nextBtn.addEventListener('click', next);
  if (edgeL) edgeL.addEventListener('click', prev);
  if (edgeR) edgeR.addEventListener('click', next);

  // ---- lightbox (optional) ---------------------------------------------------
  var lb = $('lightbox'), lbImg = $('lbImg'), lbCap = $('lbCap'), lbClose = $('lbClose');
  function openLb(src, cap) {
    if (!lb || !lbImg) return;
    lbImg.src = src;
    lbImg.alt = cap || '';
    if (lbCap) lbCap.textContent = cap || '';
    lb.hidden = false;
  }
  function closeLb() { if (lb) { lb.hidden = true; if (lbImg) lbImg.src = ''; } }
  if (lbClose) lbClose.addEventListener('click', closeLb);
  if (lb) {
    lb.addEventListener('click', function (e) { if (e.target === lb) closeLb(); });
  }
  Array.prototype.forEach.call(stage.querySelectorAll('.lbx'), function (el) {
    el.addEventListener('click', function () {
      var img = el.tagName === 'IMG' ? el : el.querySelector('img');
      if (!img) return;
      var cap = el.getAttribute('data-cap') ||
                (el.querySelector('figcaption') || {}).textContent || img.alt;
      openLb(img.currentSrc || img.src, cap);
    });
  });

  // ---- keyboard --------------------------------------------------------------
  document.addEventListener('keydown', function (e) {
    if (lb && !lb.hidden) {
      if (e.key === 'Escape') { e.preventDefault(); closeLb(); }
      return;
    }
    // The archive drawer and any real control keep their own keys.
    if (document.body.classList.contains('wn-on')) return;
    if (e.target && e.target.closest &&
        e.target.closest('button, a, input, textarea, select, audio, video, [contenteditable], summary')) {
      return;
    }
    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
      e.preventDefault(); next();
    } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
      e.preventDefault(); prev();
    } else if (e.key === 'Home') {
      e.preventDefault(); go(0, 'prev');
    } else if (e.key === 'End') {
      e.preventDefault(); go(total - 1, 'next');
    }
  });

  // ---- touch -----------------------------------------------------------------
  var x0 = null;
  stage.addEventListener('touchstart', function (e) {
    x0 = e.changedTouches[0].clientX;
  }, { passive: true });
  stage.addEventListener('touchend', function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0;
    x0 = null;
    if (Math.abs(dx) > 48) { dx < 0 ? next() : prev(); }
  }, { passive: true });

  // ---- deep link -------------------------------------------------------------
  function fromHash() {
    var id = (location.hash || '').replace('#', '');
    if (!id) return;
    for (var i = 0; i < total; i++) {
      if (slides[i].id === id) { idx = i; break; }
    }
  }
  fromHash();
  window.addEventListener('hashchange', function () {
    var before = idx;
    fromHash();
    if (before !== idx) render(idx > before ? 'next' : 'prev');
  });
  render('next');
})();
