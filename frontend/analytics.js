// Optional runtime configuration keeps local development free of analytics.
(async () => {
  try {
    const response = await fetch('/api/analytics-config', { cache: 'no-store' });
    if (!response.ok) return;
    const { measurement_id: id } = await response.json();
    if (typeof id !== 'string' || !/^G-[A-Z0-9]+$/.test(id)) return;

    // Never include query strings or fragments from incoming links.
    const pageLocation = location.origin + location.pathname;
    let referrer = '';
    try {
      const url = new URL(document.referrer);
      referrer = url.origin + url.pathname;
    } catch { /* Direct visit. */ }

    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', id, {
      page_location: pageLocation,
      page_referrer: referrer,
    });
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
    script.referrerPolicy = 'no-referrer';
    document.head.appendChild(script);
  } catch { /* Analytics availability must not affect the workbench. */ }
})();
