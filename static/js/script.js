let flashcardCount = 0;

function addFlashcard() {
    flashcardCount++;
    const flashcardsDiv = document.getElementById('flashcards');

    const cardDiv = document.createElement('div');
    cardDiv.className = 'flashcard';
    cardDiv.id = 'flashcard-' + flashcardCount;

    cardDiv.innerHTML = `
        <input type="text" placeholder="Enter term" class="term">
        <input type="text" placeholder="Enter definition" class="definition">
        <button class="remove-btn" onclick="removeFlashcard('flashcard-${flashcardCount}')">Remove</button>
    `;

    flashcardsDiv.appendChild(cardDiv);
}

function removeFlashcard(id) {
    const card = document.getElementById(id);
    if (card) {
        card.remove();
    }
}

function saveFlashcards() {
    const title = document.getElementById('title').value;
    const description = document.getElementById('description').value;
    const cards = document.querySelectorAll('.flashcard');

    const flashcards = [];
    cards.forEach(card => {
        const term = card.querySelector('.term').value;
        const definition = card.querySelector('.definition').value;
        flashcards.push({ term, definition });
    });

    console.log({
        title,
        description,
        flashcards
    });

    alert('Flashcards saved! Check the console for output.');
}

// Initialize with one flashcard
addFlashcard();
