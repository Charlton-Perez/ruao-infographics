/* Shared share-button wiring for RUAO infographic pages.
 *
 * LinkedIn and Bluesky both have "share intent" URLs that open a pre-filled
 * post in a new tab — no API keys or server needed. Neither (nor any platform)
 * supports attaching an actual image file via a share-intent URL — that's a
 * deliberate security boundary (a site can't force an upload into your
 * account), so these two only ever produce a link + the platform's own
 * auto-generated link-preview card (populated from the page's Open Graph
 * tags), not a native photo attachment.
 *
 * A real attached-photo share IS possible via the Web Share API, but only on
 * platforms/browsers that support sharing files (mainly mobile Safari/Chrome
 * through the OS share sheet) — it can't target LinkedIn or Bluesky
 * specifically, just whatever the OS offers, so it's offered as a third,
 * feature-detected "Share via device" option rather than a replacement.
 *
 * Usage (call after the buttons exist in the DOM):
 *   initShareButtons({ url, title, text, image });
 */
function initShareButtons({ url, title, text, image }) {
  const li = document.getElementById('share-linkedin');
  const bs = document.getElementById('share-bluesky');
  const nativeBtn = document.getElementById('share-native');

  if (li) li.addEventListener('click', () => {
    const href = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;
    window.open(href, '_blank', 'noopener,noreferrer,width=600,height=600');
  });

  if (bs) bs.addEventListener('click', () => {
    const href = `https://bsky.app/intent/compose?text=${encodeURIComponent(`${text} ${url}`)}`;
    window.open(href, '_blank', 'noopener,noreferrer,width=600,height=600');
  });

  if (nativeBtn && image) {
    const canShareFiles = () => {
      if (!navigator.share || !navigator.canShare) return false;
      try {
        const dummy = new File([new Blob(['x'])], 'test.png', { type: 'image/png' });
        return navigator.canShare({ files: [dummy] });
      } catch {
        return false;
      }
    };
    if (canShareFiles()) {
      nativeBtn.hidden = false;
      nativeBtn.addEventListener('click', async () => {
        try {
          const resp = await fetch(image);
          const blob = await resp.blob();
          const file = new File([blob], image.split('/').pop(), { type: blob.type || 'image/png' });
          if (navigator.canShare({ files: [file] })) {
            await navigator.share({ files: [file], title, text, url });
          } else {
            await navigator.share({ title, text, url });
          }
        } catch {
          // User cancelled the share sheet, or the fetch/share failed — no
          // action needed either way.
        }
      });
    }
  }
}
