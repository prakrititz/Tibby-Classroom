let lectureData = null;
let currentSection = 0;
let navigationCreated = false;

document.addEventListener('DOMContentLoaded', function() {
    const generateSummaryBtn = document.getElementById('generate-summary');
    const lectureContent = document.getElementById('lecture-content');
    const aiImage = document.querySelector('.ai-image img');

    generateSummaryBtn.addEventListener('click', function() {
        const topic = prompt("Enter a topic for the summary:");
        const BgBox = document.querySelector(".ai-image");
        if (topic) {
            const Spinner = document.createElement("div");
            Spinner.classList.add("spinner-div");
            Spinner.innerHTML = `<div class="loader book"><figure class="page"></figure><figure class="page"></figure><figure class="page"></figure></div><h1 class="spinner-text">Please wait as Tibby prepares your educational content</h1>`;
            BgBox.insertBefore(Spinner,BgBox.firstChild);
            fetch('/generate_summary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic: topic })
            })
            .then(response => response.json())
            .then(data => {
                lectureData = data.summary;
                renderLecture(lectureData);
                lectureContent.classList.remove('hidden');
                Spinner.remove();
            })
            .catch(error => console.error('Error:', error));
        }
    });
});

function renderLecture(data) {
    
    const aiImage = document.querySelector('.ai-image');
    const tibbySpeechBubble = document.getElementById('tibby-speech-bubble');
    const TibbyImage = document.querySelector(".ai-image img");
    
    function displayScene(index) {
        const scene = data.scenes[index];
        const backgroundImageName = scene.background_image.split('/').pop();
        aiImage.style.backgroundImage = `url('/get_background_image/${encodeURIComponent(backgroundImageName)}')`;
        tibbySpeechBubble.innerHTML = `
            <p><strong><b>${scene.dialogue.character}:</b></strong> 
            ${scene.dialogue.text}</p>
        `;
        TibbyImage.src = `/static/images/tibby_${scene.dialogue.mood.toLowerCase()}.png`
    }
    

    displayScene(currentSection);

    // Remove existing navigation menu if it exists
    const existingNavigation = document.getElementById('navigation');
    if (existingNavigation) {
        existingNavigation.remove();
    }

    // Create new navigation menu
    const navigation = document.createElement('div');
    navigation.id = 'navigation';
    navigation.innerHTML = `
        <button id="prev-btn" onclick="navigateSection(-1)">Previous</button>
        <button id="next-btn" onclick="navigateSection(1)">Next</button>
        <button id="close-summary" onclick="closeSummary()">Close Summary</button>
    `;
    aiImage.appendChild(navigation);

    updateNavigationButtons();
}


function formatText(text) {
    text = text.replace(/\*/g, '&#8727;');
    text = text.replace(/\b([a-z])\[n\]/g, '<i>$1</i>[n]');
    return text;
}

function navigateSection(direction) {
    currentSection += direction;
    if (currentSection < 0) currentSection = 0;
    if (currentSection >= lectureData.scenes.length) currentSection = lectureData.scenes.length - 1;
    renderLecture(lectureData);
}

function updateNavigationButtons() {
    document.getElementById('prev-btn').disabled = (currentSection === 0);
    document.getElementById('next-btn').disabled = (currentSection === lectureData.scenes.length - 1);
}

function closeSummary() {
    const aiImage = document.querySelector('.ai-image');
    aiImage.style.backgroundImage = '';
    document.getElementById('navigation').style.display = 'none';
    document.getElementById('tibby-speech-bubble').textContent = 'That was fun!! What would you like to learn next?';
    document.querySelector('.tibby-avatar').style.display = 'block';
}