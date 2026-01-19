/**
 * NixVir Google Analytics
 * Respects Do Not Track (DNT) browser setting
 *
 * Usage: <script src="/js/analytics.js"></script>
 */
(function() {
    var dnt = navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack;
    var doNotTrack = dnt === "1" || dnt === "yes";

    if (!doNotTrack) {
        var script = document.createElement('script');
        script.async = true;
        script.src = 'https://www.googletagmanager.com/gtag/js?id=G-E2QD5PNRWE';
        document.head.appendChild(script);

        window.dataLayer = window.dataLayer || [];
        function gtag() { dataLayer.push(arguments); }
        window.gtag = gtag;

        gtag('js', new Date());
        gtag('config', 'G-E2QD5PNRWE');
    }
})();
