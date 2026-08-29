// Shared "copy endpoint URL" behavior for [data-copy] buttons across the site.
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-copy]");
  if (!btn) return;
  const text = btn.getAttribute("data-copy");
  const done = (label) => {
    const original = btn.textContent;
    btn.textContent = label;
    btn.classList.add("copied");
    setTimeout(() => {
      btn.textContent = original;
      btn.classList.remove("copied");
    }, 1500);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(
      () => done("Copied!"),
      () => done("Copy failed")
    );
  } else {
    done("Copy failed");
  }
});
