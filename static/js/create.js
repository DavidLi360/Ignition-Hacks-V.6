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

const text = "Working memory is the short-term system the brain uses to hold and manipulate information temporarily. The spacing effect suggests that information is better recalled if learning sessions are spaced out over time. Chunking improves memory by grouping individual pieces of data into larger, meaningful units (e.g., phone numbers). The serial position effect says we tend to remember the first (primacy) and last (recency) items in a list best.";

getSummary(text).then(summary => {
    console.log(summary);
});

// user selects a docx file
document.getElementById("fileChooser").addEventListener("change", async function() {
    const file = this.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("http://127.0.0.1:5000/summarize-docx", {
        method: "POST",
        body: formData
    });

    const summary = await response.json();
    console.log(summary); // Array of summarized sentences

    // Autofill summarized sentences
    summary.forEach(sentence => {
        const flashcardsDiv = document.getElementById('flashcards');
        const cardDiv = document.createElement('div');
        cardDiv.className = 'flashcard';
        cardDiv.id = 'flashcard-' + flashcardCount;

        cardDiv.innerHTML = `
            <input type="text" placeholder="Enter term" class="term">
            <input type="text" placeholder="Enter definition" class="definition" value="${sentence}">
            <button class="remove-btn" onclick="removeFlashcard('flashcard-${flashcardCount}')">Remove</button>
        `;
        
        flashcardsDiv.appendChild(cardDiv);
        flashcardCount++;
    });
});