document.addEventListener("DOMContentLoaded", () => {
    const questionDiv = document.getElementById("question");
    const answerInput = document.getElementById("answer-input");
    const feedbackDiv = document.getElementById("feedback");
    const nextButton = document.getElementById("next-button");

    let currentAnswer = "";
    let quizOver = false;

    // tracking stats
    let totalChars = 0;
    let startTime = null;
    let similarities = [];
    let cardCount = 0;

    // Reset test and load first card
    fetch("/start_test", { method: "POST" })
        .then(() => {
            startTime = Date.now();
            loadNextCard();
        });

    function loadNextCard() {
        fetch("/get_next_card")
            .then(res => res.json())
            .then(data => {
                if (data.quiz_over) {
                    endQuiz();
                } else {
                    questionDiv.textContent = data.question;
                    currentAnswer = data.answer;
                    feedbackDiv.textContent = "";
                    answerInput.value = "";
                    answerInput.style.display = "block";
                    nextButton.style.display = "inline-block";
                    answerInput.focus();
                }
            });
    }

    function checkAnswer() {
        if (quizOver) return;

        const userAnswer = answerInput.value.trim();
        if (!userAnswer) {
            feedbackDiv.textContent = "⚠️ Please type an answer.";
            answerInput.focus();
            return;
        }

        totalChars += userAnswer.length;
        cardCount++;

        fetch("/check_answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_answer: userAnswer, correct_answer: currentAnswer })
        })
            .then(res => res.json())
            .then(data => {
                similarities.push(data.similarity);

                // Calculate stats for this card
                const elapsed = (Date.now() - startTime) / 1000; // seconds
                const minutes = elapsed / 60;
                const wpm = minutes > 0 ? Math.round((totalChars / 5) / minutes) : 0;
                const avgSim =
                    similarities.length > 0
                        ? (similarities.reduce((a, b) => a + b, 0) / similarities.length).toFixed(2)
                        : 0;

                // Send stats for this card
                fetch("/submit_result", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        wpm: wpm,
                        similarity: avgSim,
                        card: cardCount,
                        is_correct: data.is_correct
                    })
                })
                .then(res => res.json())
                .then(data => {
                    // Handle response if needed
                    const timeTilNextReview = data.time_til_next_review;
                    if (typeof timeTilNextReview === "number") {
                        let reviewMsg = "";
                        if (timeTilNextReview < 60) {
                            reviewMsg = `Next review: in ${timeTilNextReview} seconds`;
                        } else if (timeTilNextReview < 3600) {
                            reviewMsg = `Next review: in ${(timeTilNextReview / 60).toFixed(1)} minutes`;
                        } else {
                            reviewMsg = `Next review: in ${(timeTilNextReview / 3600).toFixed(2)} hours`;
                        }
                        // Show below feedback
                        const reviewDiv = document.createElement("div");
                        reviewDiv.id = "review-info";
                        reviewDiv.style.fontSize = "0.95em";
                        reviewDiv.style.color = "#888";
                        reviewDiv.textContent = reviewMsg;
                        // Remove previous if exists
                        const prev = document.getElementById("review-info");
                        if (prev) prev.remove();
                        feedbackDiv.parentNode.insertBefore(reviewDiv, feedbackDiv.nextSibling);
                    }
                    console.log("Time until next review:", timeTilNextReview);
                });

                feedbackDiv.textContent = data.is_correct
                    ? "✅ Correct!"
                    : `❌ Incorrect. Correct answer: ${currentAnswer}`;

                setTimeout(loadNextCard, 900);
            })
            .catch(() => {
                feedbackDiv.textContent = "Error checking answer.";
            });
    }

    function endQuiz() {
        quizOver = true;
        const totalTime = (Date.now() - startTime) / 1000; // seconds
        const minutes = totalTime / 60;
        const wpm = Math.round((totalChars / 5) / minutes);
        const avgSim =
            similarities.length > 0
                ? (similarities.reduce((a, b) => a + b, 0) / similarities.length).toFixed(2)
                : 0;

        questionDiv.textContent = "✅ Test Complete!";
        feedbackDiv.innerHTML = `
            <p><strong>WPM:</strong> ${wpm}</p>
            <p><strong>Average Similarity:</strong> ${avgSim}</p>
        `;
        answerInput.style.display = "none";
        nextButton.style.display = "none";
        // No need to send stats here anymore
    }

    // Submit on Enter (without newline)
    answerInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            checkAnswer();
        }
    });

    nextButton.addEventListener("click", checkAnswer);
});
