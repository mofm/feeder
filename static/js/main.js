// Define the shareFeed function
function shareFeed(url) {
    if (navigator.share) {
        navigator.share({
            title: 'Check out this feed!',
            url: url
        }).then(() => {
            console.log('Thanks for sharing!');
        }).catch(console.error);
    } else {
        // Fallback for browsers that do not support the Web Share API
        prompt('Copy this link to share:', url);
    }
}

// Attach event listeners to share buttons
document.addEventListener('DOMContentLoaded', function() {
    const shareButtons = document.querySelectorAll('.share-button');
    shareButtons.forEach(button => {
        button.addEventListener('click', function() {
            const url = this.getAttribute('data-url');
            shareFeed(url);
        });
    });
});


document.addEventListener('DOMContentLoaded', function () {
    if ('IntersectionObserver' in window) {
        const observerOptions = {
            root: null,
            rootMargin: '0px',
            threshold: 0.5
        };

        const observer = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const feedId = entry.target.getAttribute('data-feed-id');
                    if (feedId) {
                        console.log(`Feed ID: ${feedId}`);  // Debugging log
                        markAsRead(feedId);
                        observer.unobserve(entry.target);
                    }
                }
            });
        }, observerOptions);

        document.querySelectorAll('.card-deck').forEach(feed => {
            observer.observe(feed);
        });
    } else {
        console.warn('IntersectionObserver is not supported by this browser.');
    }

    function markAsRead(feedId) {
        fetch('/mark_read_ajax/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ feed_id: feedId })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                setTimeout(() => {
                    const feedElement = document.querySelector(`[data-feed-id="${feedId}"]`);
                    const readButton = feedElement.querySelector('.btn-secondary');
                    readButton.innerHTML = '<i class="fas fa-check-circle"></i> Read';
                }, 2000);  // 2000 milliseconds (2 seconds) delay
            }
        })
        .catch(error => {
            console.error('There was a problem with the fetch operation:', error);
        });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});