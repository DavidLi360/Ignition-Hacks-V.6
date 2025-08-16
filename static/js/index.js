const toggle = document.getElementById('test-toggle');
const isToggled = document.getElementById('test-is-toggled');
toggle.addEventListener('change', function () {
    isToggled.textContent = this.checked ? 'On' : 'Off';
});

toggle.addEventListener('change', function () {
    fetch('/toggle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ isToggled: this.checked })
    })
        .then(response => response.json())
        .then(data => {
            console.log('Success:', data);
        })
        .catch((error) => {
            console.error('Error:', error);
        });
});