let flashcardCount = 0;

// gets summary of a given text
async function getSummary(text) {
    const response = await fetch("http://127.0.0.1:5000/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text })
    });
    const summaryArray = await response.json();
    return summaryArray; // Array of concise sentences
}

function addFlashcard() {
    const flashcardsDiv = document.getElementById('flashcards');

    const cardDiv = document.createElement('div');
    cardDiv.className = 'flashcard';
    cardDiv.id = 'flashcard-' + flashcardCount;

    const termInput = document.createElement('input');
    termInput.type = 'text';
    termInput.placeholder = 'Enter question or term';
    termInput.className = 'term';

    const definitionInput = document.createElement('input');
    definitionInput.type = 'text';
    definitionInput.placeholder = 'Enter answer or definition';
    definitionInput.className = 'definition';

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'remove-btn';
    removeButton.textContent = 'Remove';
    removeButton.addEventListener('click', () => removeFlashcard(cardDiv.id));

    cardDiv.append(termInput, definitionInput, removeButton);

    flashcardsDiv.appendChild(cardDiv);
    flashcardCount++;
}

function removeFlashcard(id) {
    const card = document.getElementById(id);
    if (card) {
        card.remove();
    }
}

const form = document.getElementById('flashcard-form');
form.addEventListener('submit', function(event) {
    event.preventDefault();  // Prevent the default form submission
    saveFlashcards();
});

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

    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.name = 'flashcards_data'; // Must match the name Flask expects
    hiddenInput.value = JSON.stringify(flashcards);
    form.appendChild(hiddenInput);
    // alert('Flashcards saved! Check the console for output.');

    // Save the flashcards by submitting the form
    form.submit();

}

// Initialize with one flashcard
addFlashcard();

// const text = "Working memory is the short-term system the brain uses to hold and manipulate information temporarily. The spacing effect suggests that information is better recalled if learning sessions are spaced out over time. Chunking improves memory by grouping individual pieces of data into larger, meaningful units (e.g., phone numbers). The serial position effect says we tend to remember the first (primacy) and last (recency) items in a list best.";

// getSummary(text).then(summary => {
//     console.log(summary);
// });

// user selects a docx file
const fileChooser = document.getElementById("fileChooser");
if (fileChooser) {
    fileChooser.addEventListener("change", async function() {
        const file = this.files[0];
        if (!file) return;

        const fileName = file.name.toLowerCase();
        const isCsv = fileName.endsWith('.csv');

        const formData = new FormData();
        formData.append("file", file);

        const endpoint = isCsv ? "/import-csv" : "/summarize-docx";
        const response = await fetch(endpoint, {
            method: "POST",
            body: formData
        });

        const payload = await response.json();
        if (!response.ok) {
            alert(payload.error || 'Could not import file.');
            return;
        }

        const importedCards = isCsv ? payload.cards : payload;
        console.log(importedCards);

        importedCards.forEach(item => {
            const flashcardsDiv = document.getElementById('flashcards');
            const cardDiv = document.createElement('div');
            cardDiv.className = 'flashcard';
            cardDiv.id = 'flashcard-' + flashcardCount;

            const termInput = document.createElement('input');
            termInput.type = 'text';
            termInput.placeholder = 'Enter term';
            termInput.className = 'term';
            termInput.value = isCsv ? (item.term || '') : '';

            const definitionInput = document.createElement('input');
            definitionInput.type = 'text';
            definitionInput.placeholder = 'Enter definition';
            definitionInput.className = 'definition';
            definitionInput.value = isCsv ? (item.definition || '') : item;

            const removeButton = document.createElement('button');
            removeButton.type = 'button';
            removeButton.className = 'remove-btn';
            removeButton.textContent = 'Remove';
            removeButton.addEventListener('click', () => removeFlashcard(cardDiv.id));

            cardDiv.append(termInput, definitionInput, removeButton);
            flashcardsDiv.appendChild(cardDiv);
            flashcardCount++;
        });

        fileChooser.value = '';
    });
}