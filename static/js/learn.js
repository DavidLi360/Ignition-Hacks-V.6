let currentCard = null;
let typedCharacters = '';
let startTime = null;
let isCorrect = false;

document.addEventListener('DOMContentLoaded', () => {

    const inputEl = document.getElementById('answer-input');
    const quizContainer = document.getElementById('flashcard-container');
    const questionEl = document.getElementById('question');
    const typedTextEl = document.getElementById('typed-text');
    const remainingTextEl = document.getElementById('remaining-text');
    const feedbackEl = document.getElementById('feedback');
    const nextButton = document.getElementById('next-button'); 

    // Load the first card
    loadNextCard();
    startTime = Date.now();

    // Automatically focus the input field when the page loads
    inputEl.focus(); 
    
    // Add a click listener to the main container
    quizContainer.addEventListener('click', () => {
        inputEl.focus();
    });

    nextButton.addEventListener('click', () => {
        if (!isCorrect) return;
        isCorrect = false;
        inputEl.value = '';
        typedCharacters = '';

        loadNextCard();
        startTime = Date.now();
    });

    inputEl.addEventListener('input', () => {
    
        typedCharacters = inputEl.value;
        const answer = currentCard.answer;
    
        let correctCount = 0;
        let feedbackHTML = '';
    
        for (let i = 0; i < answer.length; i++) {
            const char = answer[i];
            const typedChar = typedCharacters[i];

            // Preserve spaces visually
            const displayChar = char === " " ? "&nbsp;" : char;
    
            if (typedChar === undefined) {
                console.log('no')
            } else if (typedChar === char) {
                feedbackHTML += `<span class="correct">${displayChar}</span>`;
                correctCount++;
            } else {
                feedbackHTML += `<span class="incorrect">${displayChar}</span>`;
            }
        }

        typedTextEl.innerHTML = feedbackHTML;
        remainingTextEl.textContent = answer.substring(typedCharacters.length);
    
        // If the user has typed the full answer
        if (typedCharacters.length === answer.length) {
            if (typedCharacters === answer) {
                // Correct! Move to the next card after a short delay
                feedbackEl.textContent = "Correct!";
                isCorrect = true;
                let secondsTaken = (Date.now() - startTime) / 1000;
                let wpm = Math.round((typedCharacters.length / 5) / (secondsTaken / 60));
                feedbackEl.innerHTML += `<p>Time taken: ${secondsTaken} seconds</p>`;
                feedbackEl.innerHTML += `<p>WPM: ${wpm}</p>`;
            } else {
                // Incorrect. User can correct their answer
                feedbackEl.textContent = "Incorrect. Try again.";
            }
        }
    });
    
    function loadNextCard() {
        fetch('/get_next_card')
            .then(response => response.json())
            .then(data => {
                if (data.quiz_over) {
                    endQuiz();
                } else {
                    currentCard = data;
                    questionEl.textContent = currentCard.question;
                    remainingTextEl.textContent = currentCard.answer;
                    typedTextEl.textContent = '';
                    feedbackEl.textContent = '';
                    inputEl.focus();
                }
            });
    }
    
    function endQuiz() {
        questionEl.textContent = "DONE LEARNING! TRY THE TEST NOW!";

        // Send results to the server
        // fetch('/submit_result', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify({ wpm: wpm, accuracy: accuracy })
        // }).then(() => {
            
        //     inputEl.style.display = 'none';
        //     feedbackEl.innerHTML = `<p>WPM: ${wpm}</p><p>Accuracy: ${accuracy}%</p>`;
        // });
    }
});