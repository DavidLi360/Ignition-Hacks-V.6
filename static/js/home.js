const toggle = document.getElementById('test-toggle');
const testStatus = document.getElementById('test-status');
toggle.addEventListener('change', function () {
    testStatus.textContent = this.checked ? 'On' : 'Off';
});

toggle.addEventListener('change', function () {
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