/* Shared share-button wiring for RUAO infographic pages.
 *
 * LinkedIn and Bluesky both have "share intent" URLs that open a pre-filled
 * post in a new tab — no API keys or server needed. Instagram has no such
 * web intent (it's app-only for posting), so that button instead downloads
 * the infographic image and shows a short instruction, which is the
 * standard workaround used across the web for "share to Instagram" buttons.
 *
 * Usage (call after the buttons exist in the DOM):
 *   initShareButtons({ url, title, text, image });
 */
function initShareButtons({ url, title, text, image }) {
  const li = document.getElementById('share-linkedin');
  const bs = document.getElementById('share-bluesky');
  const ig = document.getElementById('share-instagram');
  const note = document.getElementById('share-note');

  const showNote = (msg, ms = 4500) => {
    if (!note) return;
    note.textContent = msg;
    note.hidden = false;
    clearTimeout(showNote._t);
    showNote._t = setTimeout(() => { note.hidden = true; }, ms);
  };

  if (li) li.addEventListener('click', () => {
    const href = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;
    window.open(href, '_blank', 'noopener,noreferrer,width=600,height=600');
  });

  if (bs) bs.addEventListener('click', () => {
    const href = `https://bsky.app/intent/compose?text=${encodeURIComponent(`${text} ${url}`)}`;
    window.open(href, '_blank', 'noopener,noreferrer,width=600,height=600');
  });

  if (ig) ig.addEventListener('click', async () => {
    try {
      const a = document.createElement('a');
      a.href = image;
      a.download = image.split('/').pop();
      document.body.appendChild(a);
      a.click();
      a.remove();
      showNote('Image saved — open Instagram and share it from there.');
    } catch {
      showNote('Could not save the image automatically — right-click it and choose "Save image".');
    }
  });
}
