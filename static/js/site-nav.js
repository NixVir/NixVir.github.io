/**
 * Shared Navigation - Single source of truth for site nav links.
 *
 * Usage: Add a container with id="nav-links" in your nav bar,
 * then include this script. It will populate the links and
 * highlight the current page.
 *
 * For <ul> style navs:  <ul id="nav-links" class="site-nav-links"></ul>
 * For flat style navs:  <div id="nav-links" class="nav-links"></div>
 */
(function () {
    'use strict';

    var NAV_ITEMS = [
        { name: 'Snow', url: '/snow-cover.html' },
        { name: 'Dashboard', url: '/dashboard.html' },
        { name: 'Ski Industry News', url: '/ski-news.html' },
        { name: 'Data Insights', url: '/post/' },
        { name: 'About', url: '/about/' },
        { name: 'Contact', url: '/contact/' }
    ];

    var container = document.getElementById('nav-links');
    if (!container) return;

    var currentPath = window.location.pathname;
    var isListContainer = container.tagName === 'UL';

    NAV_ITEMS.forEach(function (item) {
        var a = document.createElement('a');
        a.href = item.url;
        a.textContent = item.name;

        // Mark current page
        if (currentPath === item.url || currentPath === item.url.replace(/\/$/, '')) {
            a.classList.add('current');
        }

        if (isListContainer) {
            var li = document.createElement('li');
            li.appendChild(a);
            container.appendChild(li);
        } else {
            container.appendChild(a);
        }
    });
})();
