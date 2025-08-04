document.addEventListener('DOMContentLoaded', function() {
    const chat = document.getElementById('chat');
    const form = document.getElementById('input-area');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    let conversation_history = [];
    let user_profile = {};
    let isSubmitting = false;
    
    // Add question counter display
    const questionCounter = document.createElement('div');
    questionCounter.id = 'question-counter';
    questionCounter.style.cssText = 'text-align: center; color: #666; font-size: 12px; margin-bottom: 10px; padding: 5px; background: #f0f0f0; border-radius: 4px;';
    chat.parentNode.insertBefore(questionCounter, chat);
    
    function updateQuestionCounter() {
        let assistantQuestions = 0;
        for (let msg of conversation_history) {
            if (msg.role === 'assistant' && msg.content.trim().endsWith('?')) {
                assistantQuestions++;
            }
        }
        const questionsRemaining = 10 - assistantQuestions;
        if (questionsRemaining > 0) {
            questionCounter.textContent = `Questions remaining before recommendations: ${questionsRemaining}`;
            questionCounter.style.color = questionsRemaining <= 2 ? '#e74c3c' : '#666';
        } else {
            questionCounter.textContent = 'Ready to give recommendations!';
            questionCounter.style.color = '#27ae60';
        }
    }

    function appendMessage(sender, text) {
        const div = document.createElement('div');
        div.className = 'msg ' + sender;
        
        // Format the text with proper line breaks and styling
        let formattedText = text
            .replace(/\\n/g, '<br>')  // Handle escaped newlines
            .replace(/\n/g, '<br>')   // Handle actual newlines
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')  // Markdown links
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold text
            .replace(/\*(.*?)\*/g, '<em>$1</em>')              // Italic text
            .replace(/### (.*?)(?=<br>|$)/g, '<h3>$1</h3>')    // Headers
            .replace(/## (.*?)(?=<br>|$)/g, '<h4>$1</h4>')     // Sub-headers
            .replace(/### (.*?)(?=<br>|$)/g, '<h3>$1</h3>')    // Headers (again for nested)
            .replace(/\*\* (.*?)(?=<br>|$)/g, '<li><strong>$1</strong></li>')  // Bold list items
            .replace(/^\d+\.\s\*\*(.*?)\*\*/gm, '<li><strong>$1</strong></li>')  // Numbered bold items
            .replace(/^\d+\.\s(.*?)(?=<br>|$)/gm, '<li>$1</li>')  // Numbered list items
            .replace(/^\*\s(.*?)(?=<br>|$)/gm, '<li>$1</li>')     // Bullet list items
            .replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');         // Wrap lists in ul tags
        
        div.innerHTML = `<b>${sender === 'user' ? 'You' : 'Assistant'}:</b> ` + formattedText;
        chat.appendChild(div);
        chat.scrollTop = chat.scrollHeight;
        updateQuestionCounter();
    }

    // Show initial welcome message
    const welcomeMessage = "Hi! I'd love to help you find the perfect haircare products. Tell me a bit about your hair - what's your hair story?";
    appendMessage('bot', welcomeMessage);
    conversation_history.push({ role: 'assistant', content: welcomeMessage });
    updateQuestionCounter();

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;
        
        // Prevent double submission
        if (isSubmitting) {
            console.log('Preventing double submission');
            return;
        }
        isSubmitting = true;
        
        appendMessage('user', text);
        conversation_history.push({ role: 'user', content: text });
        userInput.value = '';
        userInput.disabled = true;
        sendBtn.disabled = true;
        
        // Create typing indicator with animated dots
        const typingDiv = document.createElement('div');
        typingDiv.className = 'msg bot typing-indicator';
        typingDiv.innerHTML = '<b>Assistant:</b> <span class="dots"></span>';
        chat.appendChild(typingDiv);
        chat.scrollTop = chat.scrollHeight;
        
        // Animate the dots
        let dotCount = 0;
        const dotsElement = typingDiv.querySelector('.dots');
        const typingInterval = setInterval(() => {
            dotCount = (dotCount + 1) % 4;
            dotsElement.textContent = '.'.repeat(dotCount);
        }, 500);
        
        try {
            console.log('Sending conversation history:', conversation_history);
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    conversation_history: conversation_history, 
                    user_profile: user_profile 
                })
            });
            if (!res.ok) {
                throw new Error('Server error: ' + res.status);
            }
            const data = await res.json();
            console.log('Received response:', data);
            
            // Update user profile with any new information
            user_profile = data.profile || user_profile;
            
            let reply = '';
            if (data.recommendation) {
                reply = data.recommendation;
            } else if (data.message) {
                reply = data.message;
            } else {
                reply = 'Sorry, I did not understand.';
            }
            
            // Remove any "Assistant:" prefix from the response to prevent duplication
            reply = reply.replace(/^Assistant:\s*/i, '').trim();
            
            // Add assistant response to conversation history
            conversation_history.push({ role: 'assistant', content: reply });
            
            // Remove the typing indicator
            clearInterval(typingInterval);
            chat.removeChild(typingDiv);
            appendMessage('bot', reply);
        } catch (err) {
            clearInterval(typingInterval);
            chat.removeChild(typingDiv);
            appendMessage('bot', 'Error: ' + err.message);
            console.error(err);
        }
        userInput.disabled = false;
        sendBtn.disabled = false;
        isSubmitting = false;
        userInput.focus();
    });
}); 