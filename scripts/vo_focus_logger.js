// Parity voice recording kit (docs/voice-recording.md): paste the whole file into the browser console on a store page before
// recording. It posts every focus stop and every VoiceOver-cursor change (aria-activedescendant) to the local server, which keeps
// them only when started with PARITY_VOICE_FOCUSLOG=1. Times are Date.now(): the clock the recorder and the captions share.
(function () {
  if (window.__parityFocusLog) { console.log("Parity focus logger: already on"); return; }
  var log = (window.__parityFocusLog = []);
  var endpoint = location.origin + "/api/voice/focuslog";
  function pathOf(node) {  // the same path the capture stage writes as css_path (parity/pipeline/capture.py)
    if (!node || node.nodeType !== 1) return "";
    var t = node.tagName.toLowerCase();
    if (node.id) return t + "#" + CSS.escape(node.id);
    if (t === "body" || t === "html") return t;
    var i = 1, sib = node;
    while ((sib = sib.previousElementSibling)) if (sib.tagName === node.tagName) i++;
    var parent = pathOf(node.parentElement);
    return (parent ? parent + " > " : "") + t + ":nth-of-type(" + i + ")";
  }
  function post(entry) {
    log.push(entry);
    fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(entry), keepalive: true })
      .then(function (r) { if (!r.ok) console.warn("Parity focus logger: the server answered " + r.status + " (start it with PARITY_VOICE_FOCUSLOG=1)"); })
      .catch(function (e) { console.warn("Parity focus logger: " + e); });
  }
  document.addEventListener("focusin", function (e) {
    var el = e.target;
    if (!el || el.nodeType !== 1) return;
    post({ t_ms: Date.now(), dom_id: el.id || pathOf(el), event: "focusin" });
  }, true);
  new MutationObserver(function (records) {
    for (var k = 0; k < records.length; k++) {
      var v = records[k].target.getAttribute("aria-activedescendant");
      if (v) post({ t_ms: Date.now(), dom_id: v, event: "activedescendant" });
    }
  }).observe(document.documentElement, { attributes: true, subtree: true, attributeFilter: ["aria-activedescendant"] });
  console.log("Parity focus logger: on, posting to " + endpoint);
})();
