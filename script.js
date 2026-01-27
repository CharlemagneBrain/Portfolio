/**
 * Research Portfolio - Charles Abdoulaye NGOM
 * Minimal JavaScript for enhanced interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Smooth scroll for anchor links
    initSmoothScroll();

    // Animate sections on scroll
    initScrollAnimations();

    // Add hover effects for external links
    initLinkEffects();

    // Console welcome message
    printConsoleMessage();
});

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
    // Add arrow icon to external links in main content
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.querySelectorAll('a[target="_blank"]').forEach(link => {
            // Skip links that already have icons
            if (!link.querySelector('i') && !link.classList.contains('pub-link')) {
                link.classList.add('external-link');
            }
        });
    }

    // Add external link indicator style
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
