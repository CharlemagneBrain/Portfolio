/**
 * Research Portfolio - Charles Abdoulaye NGOM
 * JavaScript for navigation, dynamic publications, pagination, and interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    initMobileNav();
    initSmoothScroll();
    initScrollAnimations();
    initLinkEffects();
    initActiveNavTracking();
    loadPublications();
    printConsoleMessage();
});

/* ========================================
   Mobile Navigation
   ======================================== */

function initMobileNav() {
    var toggle = document.querySelector('.mobile-nav-toggle');
    var menu = document.querySelector('.mobile-nav-menu');
    var links = document.querySelectorAll('.mobile-nav-link');

    if (!toggle || !menu) return;

    toggle.addEventListener('click', function() {
        toggle.classList.toggle('active');
        menu.classList.toggle('active');
    });

    links.forEach(function(link) {
        link.addEventListener('click', function() {
            toggle.classList.remove('active');
            menu.classList.remove('active');
        });
    });

    document.addEventListener('click', function(e) {
        if (!toggle.contains(e.target) && !menu.contains(e.target)) {
            toggle.classList.remove('active');
            menu.classList.remove('active');
        }
    });
}

function initActiveNavTracking() {
    var sections = document.querySelectorAll('section[id]');
    var navLinks = document.querySelectorAll('.mobile-nav-link');

    if (sections.length === 0 || navLinks.length === 0) return;

    var updateActiveLink = debounce(function() {
        var scrollPosition = window.scrollY + 100;

        sections.forEach(function(section) {
            var sectionTop = section.offsetTop;
            var sectionHeight = section.offsetHeight;
            var sectionId = section.getAttribute('id');

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                navLinks.forEach(function(link) {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === '#' + sectionId) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }, 100);

    window.addEventListener('scroll', updateActiveLink);
    updateActiveLink();
}

/* ========================================
   Dynamic Publications from JSON
   ======================================== */

var ITEMS_PER_PAGE = 3;
var pubState = { publications: [], currentPage: 1, totalPages: 1 };

function loadPublications() {
    fetch('data/publications.json')
        .then(function(response) {
            if (!response.ok) throw new Error('Failed to load publications');
            return response.json();
        })
        .then(function(data) {
            pubState.publications = data.publications || [];
            pubState.totalPages = Math.max(1, Math.ceil(pubState.publications.length / ITEMS_PER_PAGE));
            renderStats(data);
            renderPage(1);
            initPaginationControls();
        })
        .catch(function(err) {
            console.error('Error loading publications:', err);
            document.getElementById('publications-container').innerHTML =
                '<p class="pub-loading">Failed to load publications. Please refresh the page.</p>';
        });
}

function renderStats(data) {
    var statsEl = document.getElementById('publications-stats');
    if (!statsEl || !data.author) return;

    var a = data.author;
    statsEl.innerHTML =
        '<a href="https://scholar.google.fr/citations?user=' + a.scholar_id + '" target="_blank" rel="noopener">Google Scholar</a> &middot; ' +
        data.total + ' publications &middot; ' +
        a.citations + ' citations &middot; h-index: ' + a.h_index;
}

function renderPage(page) {
    pubState.currentPage = page;

    var container = document.getElementById('publications-container');
    if (!container) return;

    var start = (page - 1) * ITEMS_PER_PAGE;
    var end = Math.min(start + ITEMS_PER_PAGE, pubState.publications.length);
    var pageItems = pubState.publications.slice(start, end);

    var html = '';
    pageItems.forEach(function(pub, i) {
        html += renderPublication(pub);
        if (i < pageItems.length - 1) {
            html += '<div class="pub-divider"></div>';
        }
    });

    container.innerHTML = html;

    // Update pagination display
    var currentPageSpan = document.getElementById('current-page');
    var totalPagesSpan = document.getElementById('total-pages');
    var prevBtn = document.getElementById('prev-page');
    var nextBtn = document.getElementById('next-page');
    var paginationEl = document.getElementById('publications-pagination');

    if (currentPageSpan) currentPageSpan.textContent = page;
    if (totalPagesSpan) totalPagesSpan.textContent = pubState.totalPages;
    if (prevBtn) prevBtn.disabled = page === 1;
    if (nextBtn) nextBtn.disabled = page === pubState.totalPages;

    // Show pagination only if more than 1 page
    if (paginationEl) {
        paginationEl.style.display = pubState.totalPages > 1 ? 'flex' : 'none';
    }
}

function renderPublication(pub) {
    var authorsHtml = highlightAuthor(escapeHtml(pub.authors));

    var citationBadge = '';
    if (pub.citations > 0) {
        citationBadge = '<span class="pub-badge">' + pub.citations +
            (pub.citations === 1 ? ' citation' : ' citations') + '</span>';
    }

    var linkHtml = '';
    if (pub.url) {
        linkHtml += '<a href="' + escapeHtml(pub.url) + '" class="pub-link" target="_blank" rel="noopener">' +
            '<i class="fas fa-link"></i> Link</a>';
    }
    if (pub.pdf_url) {
        linkHtml += '<a href="' + escapeHtml(pub.pdf_url) + '" class="pub-link" target="_blank" rel="noopener">' +
            '<i class="fas fa-file-pdf"></i> PDF</a>';
    }

    return '<article class="publication">' +
        '<div class="pub-year">' + escapeHtml(pub.year) + '</div>' +
        '<div class="pub-details">' +
            '<h3 class="pub-title">' +
                (pub.url
                    ? '<a href="' + escapeHtml(pub.url) + '" target="_blank" rel="noopener">' + escapeHtml(pub.title) + '</a>'
                    : escapeHtml(pub.title)) +
            '</h3>' +
            '<p class="pub-authors">' + authorsHtml + '</p>' +
            (pub.venue ? '<p class="pub-venue">' + escapeHtml(pub.venue) + '</p>' : '') +
            citationBadge +
            (linkHtml ? '<div class="pub-links">' + linkHtml + '</div>' : '') +
        '</div>' +
    '</article>';
}

function highlightAuthor(authors) {
    // Bold "CA Ngom" or similar variations
    return authors
        .replace(/(CA Ngom)/gi, '<strong>$1</strong>')
        .replace(/(C\.?A\.? Ngom)/gi, '<strong>$1</strong>')
        .replace(/(Charles A(?:bdoulaye)? Ngom)/gi, '<strong>$1</strong>');
}

function initPaginationControls() {
    var prevBtn = document.getElementById('prev-page');
    var nextBtn = document.getElementById('next-page');

    if (prevBtn) {
        prevBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (pubState.currentPage > 1) {
                renderPage(pubState.currentPage - 1);
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (pubState.currentPage < pubState.totalPages) {
                renderPage(pubState.currentPage + 1);
            }
        });
    }
}

/* ========================================
   Smooth Scroll
   ======================================== */

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            var targetId = this.getAttribute('href');
            var targetElement = document.querySelector(targetId);

            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

/* ========================================
   Scroll Animations
   ======================================== */

function initScrollAnimations() {
    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { root: null, rootMargin: '0px', threshold: 0.1 });

    document.querySelectorAll('.section').forEach(function(section) {
        section.classList.add('animate-on-scroll');
        observer.observe(section);
    });

    var style = document.createElement('style');
    style.textContent =
        '.animate-on-scroll { opacity: 0; transform: translateY(20px); transition: opacity 0.6s ease-out, transform 0.6s ease-out; }' +
        '.animate-on-scroll.visible { opacity: 1; transform: translateY(0); }';
    document.head.appendChild(style);
}

/* ========================================
   External Link Effects
   ======================================== */

function initLinkEffects() {
    var mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.querySelectorAll('a[target="_blank"]').forEach(function(link) {
            if (!link.querySelector('i') && !link.classList.contains('pub-link')) {
                link.classList.add('external-link');
            }
        });
    }

    var style = document.createElement('style');
    style.textContent =
        '.external-link::after { content: "\\2197"; font-size: 0.75em; margin-left: 0.2em; opacity: 0.7; transition: opacity 0.2s ease; }' +
        '.external-link:hover::after { opacity: 1; }';
    document.head.appendChild(style);
}

/* ========================================
   Utilities
   ======================================== */

function debounce(func, wait) {
    var timeout;
    return function() {
        var context = this;
        var args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(function() { func.apply(context, args); }, wait);
    };
}

function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

function printConsoleMessage() {
    console.log('%cWelcome to my portfolio!', 'color: #2563eb; font-size: 14px; font-weight: bold; padding: 10px');
    console.log('%cCharles Abdoulaye NGOM - PhD Student in AI', 'color: #4a4a4a; font-size: 12px');
    console.log('%ccharles.ngom@inrae.fr', 'color: #4a4a4a; font-size: 12px');
}

(function() {
    var footerYear = document.querySelector('.footer p');
    if (footerYear) {
        footerYear.innerHTML = footerYear.innerHTML.replace(/\d{4}/, new Date().getFullYear());
    }
})();
