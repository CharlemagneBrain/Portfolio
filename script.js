/**
 * Research Portfolio - Charles Abdoulaye NGOM
 * JavaScript for navigation, pagination, and interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile navigation
    initMobileNav();

    // Initialize publications pagination
    initPagination();

    // Smooth scroll for anchor links
    initSmoothScroll();

    // Animate sections on scroll
    initScrollAnimations();

    // Add hover effects for external links
    initLinkEffects();

    // Update active nav link on scroll
    initActiveNavTracking();

    // Console welcome message
    printConsoleMessage();
});

/**
 * Mobile Navigation
 */
function initMobileNav() {
    const toggle = document.querySelector('.mobile-nav-toggle');
    const menu = document.querySelector('.mobile-nav-menu');
    const links = document.querySelectorAll('.mobile-nav-link');

    if (!toggle || !menu) return;

    toggle.addEventListener('click', function() {
        toggle.classList.toggle('active');
        menu.classList.toggle('active');
    });

    // Close menu when clicking a link
    links.forEach(link => {
        link.addEventListener('click', function() {
            toggle.classList.remove('active');
            menu.classList.remove('active');
        });
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!toggle.contains(e.target) && !menu.contains(e.target)) {
            toggle.classList.remove('active');
            menu.classList.remove('active');
        }
    });
}

/**
 * Active navigation link tracking
 */
function initActiveNavTracking() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.mobile-nav-link');

    if (sections.length === 0 || navLinks.length === 0) return;

    const updateActiveLink = debounce(function() {
        const scrollPosition = window.scrollY + 100;

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute('id');

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === `#${sectionId}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }, 100);

    window.addEventListener('scroll', updateActiveLink);
    updateActiveLink();
}

/**
 * Publications Pagination
 */
function initPagination() {
    const container = document.getElementById('publications-container');
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const currentPageSpan = document.getElementById('current-page');
    const totalPagesSpan = document.getElementById('total-pages');

    if (!container || !prevBtn || !nextBtn) return;

    const publications = container.querySelectorAll('.publication[data-page]');
    const dividers = container.querySelectorAll('.pub-divider[data-page]');
    const itemsPerPage = 5;
    const totalPages = Math.ceil(publications.length / itemsPerPage);
    let currentPage = 1;

    // Update total pages display
    if (totalPagesSpan) {
        totalPagesSpan.textContent = totalPages;
    }

    function showPage(page) {
        currentPage = page;

        // Update page indicator
        if (currentPageSpan) {
            currentPageSpan.textContent = page;
        }

        // Calculate range
        const startIndex = (page - 1) * itemsPerPage;
        const endIndex = startIndex + itemsPerPage;

        // Show/hide publications
        publications.forEach((pub, index) => {
            if (index >= startIndex && index < endIndex) {
                pub.classList.add('active');
            } else {
                pub.classList.remove('active');
            }
        });

        // Show/hide dividers (between visible items only)
        dividers.forEach((div, index) => {
            if (index >= startIndex && index < endIndex - 1) {
                div.classList.add('active');
            } else {
                div.classList.remove('active');
            }
        });

        // Update button states
        prevBtn.disabled = page === 1;
        nextBtn.disabled = page === totalPages;

        // Scroll to publications section
        if (page !== 1) {
            const pubSection = document.getElementById('publications');
            if (pubSection) {
                pubSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    }

    // Event listeners
    prevBtn.addEventListener('click', function() {
        if (currentPage > 1) {
            showPage(currentPage - 1);
        }
    });

    nextBtn.addEventListener('click', function() {
        if (currentPage < totalPages) {
            showPage(currentPage + 1);
        }
    });

    // Initialize first page
    showPage(1);
}

/**
 * Smooth scrolling for internal anchor links
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Animate elements when they come into view
 */
function initScrollAnimations() {
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.add('animate-on-scroll');
        observer.observe(section);
    });

    // Add CSS for animations
    const style = document.createElement('style');
    style.textContent = `
        .animate-on-scroll {
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.6s ease-out, transform 0.6s ease-out;
        }
        .animate-on-scroll.visible {
            opacity: 1;
            transform: translateY(0);
        }
    `;
    document.head.appendChild(style);
}

/**
 * Add subtle effects for external links
 */
function initLinkEffects() {
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.querySelectorAll('a[target="_blank"]').forEach(link => {
            if (!link.querySelector('i') && !link.classList.contains('pub-link')) {
                link.classList.add('external-link');
            }
        });
    }

    const style = document.createElement('style');
    style.textContent = `
        .external-link::after {
            content: '\\2197';
            font-size: 0.75em;
            margin-left: 0.2em;
            opacity: 0.7;
            transition: opacity 0.2s ease;
        }
        .external-link:hover::after {
            opacity: 1;
        }
    `;
    document.head.appendChild(style);
}

/**
 * Print a welcome message to the console
 */
function printConsoleMessage() {
    const styles = [
        'color: #2563eb',
        'font-size: 14px',
        'font-weight: bold',
        'padding: 10px'
    ].join(';');

    console.log('%cWelcome to my portfolio!', styles);
    console.log('%cI\'m Charles Abdoulaye NGOM, a PhD Student in AI.', 'color: #4a4a4a; font-size: 12px;');
    console.log('%cFeel free to reach out: charles.ngom@inrae.fr', 'color: #4a4a4a; font-size: 12px;');
    console.log('%c---', 'color: #e5e5e5');
}

/**
 * Utility: Debounce function for performance
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Update copyright year automatically
 */
(function updateCopyrightYear() {
    const footerYear = document.querySelector('.footer p');
    if (footerYear) {
        const currentYear = new Date().getFullYear();
        footerYear.innerHTML = footerYear.innerHTML.replace(/\d{4}/, currentYear);
    }
})();
