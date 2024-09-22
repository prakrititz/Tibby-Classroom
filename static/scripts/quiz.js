document.addEventListener('DOMContentLoaded', function() {
    const generateQuizBtn = document.getElementById('generate-quiz');
    const quizContainer = document.getElementById('quiz-container');
    const quizTopic = document.getElementById('quiz-topic');
    const questionsContainer = document.getElementById('questions');
    const submitQuizBtn = document.getElementById('submit-quiz');
    const quizResults = document.getElementById('quiz-results');
    const loadingIndicator = document.getElementById('loading-indicator');

    generateQuizBtn.addEventListener('click', function() {
        const topic = prompt("Enter a topic for the quiz:");
        if (topic) {
            loadingIndicator.classList.remove('hidden');
            fetch('/create_quiz', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic: topic, num_questions: 5 })
            })
            .then(response => response.json())
            .then(data => {
                renderQuiz(data);
                quizContainer.classList.remove('hidden');
                loadingIndicator.classList.add('hidden');
            })
            .catch(error => {
                console.error('Error:', error);
                loadingIndicator.classList.add('hidden');
            });
        }
    });

    function renderQuiz(quizData) {
        quizTopic.textContent = `Quiz on: ${quizData.topic}`;
        quizTopic.style.color = "white";
        quizTopic.style.fontWeight = "bold";
        questionsContainer.innerHTML = '';

        quizData.questions.forEach((question, index) => {
            const questionElement = document.createElement('div');
            questionElement.classList.add('question');
            questionElement.innerHTML = `
                <p><strong>Question ${index + 1}:</strong> ${question.question_text}</p>
                <div class="options">
                    ${question.options.map((option, optIndex) => `
                        <button class="quiz-option" data-question="${index}" data-option="${optIndex}">
                            ${option.text}
                        </button>
                    `).join('')}
                </div>
            `;
            questionsContainer.appendChild(questionElement);
        });

        submitQuizBtn.classList.remove('hidden');
        
        // Add event listeners to quiz options
        document.querySelectorAll('.quiz-option').forEach(option => {
            option.addEventListener('click', function() {
                const questionIndex = this.getAttribute('data-question');
                document.querySelectorAll(`.quiz-option[data-question="${questionIndex}"]`).forEach(opt => {
                    opt.classList.remove('selected');
                });
                this.classList.add('selected');
            });
        });
    }

    submitQuizBtn.addEventListener('click', function() {
        const answers = {};
        document.querySelectorAll('.question').forEach((questionEl, index) => {
            const selectedOption = questionEl.querySelector('.quiz-option.selected');
            if (selectedOption) {
                answers[index] = selectedOption.textContent.trim();
            }
        });

        loadingIndicator.classList.remove('hidden');
        fetch('/submit_quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers: answers })
        })
        .then(response => response.json())
        .then(data => {
            document.querySelectorAll('.question').forEach((questionEl, index) => {
                const selectedOption = questionEl.querySelector('.quiz-option.selected');
                if (selectedOption.textContent.trim()!=data.correct_answers[index].text.trim()) {
                    selectedOption.style.backgroundColor = "red";
                }
            });
            document.querySelectorAll(".question").forEach((question,index)=>{
                const correctOption = question.querySelectorAll(".quiz-option").forEach((option,index1)=>{
                    if(option.textContent.trim()==data.correct_answers[index].text.trim()){
                        option.style.backgroundColor = "green";
                    }
                })
                const ExplanationBox = document.createElement("div");
                ExplanationBox.classList.add("question-explanation");
                ExplanationBox.innerHTML = `<h3><b>Explanation</b></h3><br><p>${data.correct_answers[index].explanation.trim()}</p>`;
                question.appendChild(ExplanationBox);
            })
            document.getElementById('score').textContent = `${data.score} / ${data.total_questions}`;
            document.getElementById('percentage').textContent = data.percentage.toFixed(2);
            quizResults.classList.remove('hidden');
            submitQuizBtn.classList.add('hidden');
            loadingIndicator.classList.add('hidden');
        })
        .catch(error => {
            console.error('Error:', error);
            loadingIndicator.classList.add('hidden');
        });
    });
});