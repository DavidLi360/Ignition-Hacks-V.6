const toggle = document.getElementById('test-toggle');
const testStatus = document.getElementById('test-status');
if (toggle && testStatus) {
    toggle.addEventListener('change', function () {
        testStatus.textContent = this.checked ? 'On' : 'Off';

        fetch('/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: this.checked })
        })
            .then(response => response.json())
            .then(data => {
                console.log('Success:', data);
            })
            .catch((error) => {
                console.error('Error:', error);
            });
    });
}

const reviewExtraToggle = document.getElementById('review-extra-toggle');
const reviewExtraStatus = document.getElementById('review-extra-status');
if (reviewExtraToggle && reviewExtraStatus) {
    reviewExtraToggle.addEventListener('change', function () {
        reviewExtraStatus.textContent = this.checked ? 'On' : 'Off';

        fetch('/toggle-extra', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: this.checked })
        })
            .then(response => response.json())
            .then(data => {
                console.log('Success:', data);
            })
            .catch((error) => {
                console.error('Error:', error);
            });
    });
}

for (const button of document.querySelectorAll('[data-set-button]')) {
    button.addEventListener('click', function () {
        const setId = this.id;
        const isTestMode = toggle && toggle.checked;
        const targetUrl = isTestMode ? `/test/${setId}` : `/learn/${setId}`;
        window.location.href = targetUrl;
    });
}