// Whole-card click-to-navigate for MCP cards on the home page.
//
// Every `.card-clickable` card (see index.html, both the static fallback
// markup and the cards rendered from agents.json) carries a `data-href`
// pointing at its detail page. Clicking anywhere on the card navigates
// there, EXCEPT the "Copy" endpoint button and the "Add to Claude" link,
// which must keep working on their own (copy to clipboard / open the
// connector URL) instead of triggering the card navigation.
//
// The listener is attached once to the `#agent-list` container rather than
// to individual cards, since the cards are re-rendered (via innerHTML) once
// agents.json loads.
document.addEventListener("DOMContentLoaded", () => {
  const list = document.getElementById("agent-list");
  if (!list) return;

  list.addEventListener("click", (e) => {
    // The copy button has its own click handler (js/copy.js) — don't
    // navigate away from under it.
    if (e.target.closest(".endpoint-copy")) return;

    // Any real link inside the card (the title, or the "Add to Claude"
    // button) should just follow its own href natively.
    if (e.target.closest("a")) return;

    const card = e.target.closest(".card-clickable");
    if (card && card.dataset.href) {
      window.location.href = card.dataset.href;
    }
  });
});
