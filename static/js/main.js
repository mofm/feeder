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