// Define the getCookie function
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

// Define the toggleFavorite function
function toggleFavorite(feedId, action) {
    fetch('/favops/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ feed_id: feedId, action: action })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            const feedElement = document.querySelector(`[data-feed-id="${feedId}"]`);
            const favoriteButton = feedElement.querySelector('.btn-favorite');
            if (action === 'add') {
                favoriteButton.innerHTML = '<i class="fas fa-heart"></i>';
                favoriteButton.setAttribute('data-action', 'remove');
                favoriteButton.classList.add('favorited');
            } else {
                favoriteButton.innerHTML = '<i class="far fa-heart"></i>';
                favoriteButton.setAttribute('data-action', 'add');
                favoriteButton.classList.remove('favorited');
            }
        }
    })
    .catch(error => {
        console.error('There was a problem with the fetch operation:', error);
    });
}

// Attach event listeners to favorite buttons
document.addEventListener('DOMContentLoaded', function() {
    const favoriteButtons = document.querySelectorAll('.btn-favorite');
    favoriteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const feedId = this.closest('[data-feed-id]').getAttribute('data-feed-id');
            const action = this.getAttribute('data-action');
            toggleFavorite(feedId, action);
        });
    });
});

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

// Automatically mark feeds as read when they are in the viewport
document.addEventListener('DOMContentLoaded', function () {
    if ('IntersectionObserver' in window) {
        const observerOptions = {
            root: null,
            rootMargin: '100px 0px',
            threshold: 0.5
        };

        const observer = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const feedElement = entry.target;
                    const feedId = feedElement.getAttribute('data-feed-id');
                    const readButton = feedElement.querySelector('.btn-secondary');

                    // Check if the feed is already marked as read
                    if (feedId && !readButton.innerHTML.includes('fa-check-circle')) {
                        console.log(`Feed ID: ${feedId}`);
                        markAsRead(feedId);
                        observer.unobserve(feedElement);
                    }
                }
            });
        }, observerOptions);

        // Use efficient selector to query elements
        const feeds = document.querySelectorAll('.card-deck');
        feeds.forEach(feed => {
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
});