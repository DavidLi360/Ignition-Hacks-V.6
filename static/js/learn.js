let currentCard = null;
let typedCharacters = '';
let startTime = null;
let isCorrect = false;
const COPY_DELAY_MS = 3500;
let canType = false;
let revealTimer = null;
let countdownTimer = null;

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
        if (!canType || !currentCard) {
            inputEl.value = '';
            return;
        }
    
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
                let secondsTaken = startTime ? (Date.now() - startTime) / 1000 : 0;
                let wpm = secondsTaken > 0
                    ? Math.round((typedCharacters.length / 5) / (secondsTaken / 60))
                    : 0;
                feedbackEl.innerHTML += `<p>Time taken: ${secondsTaken} seconds</p>`;
                feedbackEl.innerHTML += `<p>WPM: ${wpm}</p>`;
            } else {
                // Incorrect. User can correct their answer
                feedbackEl.textContent = "Incorrect. Try again.";
            }
        }
    });

    function clearUnlockTimers() {
        if (revealTimer) {
            clearTimeout(revealTimer);
            revealTimer = null;
        }
        if (countdownTimer) {
            clearInterval(countdownTimer);
            countdownTimer = null;
        }
    }

    function lockTypingUntilReady(answer) {
        clearUnlockTimers();

        canType = false;
        inputEl.disabled = true;
        inputEl.value = '';
        typedTextEl.textContent = '';
        remainingTextEl.textContent = '';

        const unlockAt = Date.now() + COPY_DELAY_MS;
        const updateCountdown = () => {
            const msLeft = Math.max(0, unlockAt - Date.now());
            const secondsLeft = Math.ceil(msLeft / 1000);
            feedbackEl.textContent = `Read the question first... answer unlocks in ${secondsLeft}s`;
        };

        updateCountdown();
        countdownTimer = setInterval(updateCountdown, 200);

        revealTimer = setTimeout(() => {
            clearUnlockTimers();
            canType = true;
            inputEl.disabled = false;
            remainingTextEl.textContent = answer;
            feedbackEl.textContent = "Now type the answer from memory.";
            startTime = Date.now();
            inputEl.focus();
        }, COPY_DELAY_MS);
    }
    
    function loadNextCard() {
        fetch('/get_next_card')
            .then(response => response.json())
            .then(data => {
                if (data.quiz_over) {
                    endQuiz();
                } else {
                    currentCard = data;
                    questionEl.textContent = currentCard.question;
                    lockTypingUntilReady(currentCard.answer);
                }
            });
    }
    
    function endQuiz() {
        clearUnlockTimers();
        canType = false;
        inputEl.disabled = true;
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