/* Shared share-button wiring for RUAO infographic pages.
 *
 * LinkedIn and Bluesky both have "share intent" URLs that open a pre-filled
 * post in a new tab — no API keys or server needed.
 *
 * Usage (call after the buttons exist in the DOM):
 *   initShareButtons({ url, title, text });
 */
function initShareButtons({ url, title, text }) {
  const li = document.getElementById('share-linkedin');
  const bs = document.getElementById('share-bluesky');

  if (li) li.addEventListener('click', () => {
    const href = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;
    window.open(href, '_blank', 'noopener,noreferrer,width=600,height=600');
  });

  if (bs) bs.addEventListener('click', () => {
    const href = `https://bsky.app/intent/compose?text=${encodeURIComponent(`${text} ${url}`)}`;
    window.open(href, '_blank', 'noopener,noreferrer,width=600,height=600');
  });
}
