document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.querySelector('.chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-message');
    function addMessage(message, isUser = true) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'ai-message');
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    function sendMessage() {
        const message = chatInput.value.trim();
        if (message) {
            addMessage(message);
            chatInput.value = '';
            fetch('/ragchat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            })
            .then(response => response.json())
            .then(data => {
                addMessage(data.response, false);
                // Display sources if needed
                console.log('Sources:', data.sources);
            })
            .catch(error => {
                console.error('Error:', error);
                addMessage('An error occurred while processing your message.', false);
            });
        }
    }
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
//completely new file