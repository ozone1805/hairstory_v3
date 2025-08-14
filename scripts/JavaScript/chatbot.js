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

    function appendMessage(sender, text, productImages = []) {
        const div = document.createElement('div');
        div.className = 'msg ' + sender;
        
        // Format the text with proper line breaks and styling
        let formattedText = text
            .replace(/\\n/g, '<br>')  // Handle escaped newlines
            .replace(/\n/g, '<br>')   // Handle actual newlines
            // Clean up any malformed HTML that the AI might generate
            .replace(/(https?:\/\/[^"'\s]+)"[^"]*"[^>]*>[^<]*/g, '$1')  // Remove malformed HTML with text after >
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')  // Markdown links
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold text
            .replace(/\*(.*?)\*/g, '<em>$1</em>')              // Italic text
            .replace(/(https?:\/\/(?:www\.)?[^\s<>"']+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">here</a>')  // Plain URLs (after other formatting)
            .replace(/### (.*?)(?=<br>|$)/g, '<h3>$1</h3>')    // Headers
            .replace(/## (.*?)(?=<br>|$)/g, '<h4>$1</h4>')     // Sub-headers
            .replace(/### (.*?)(?=<br>|$)/g, '<h3>$1</h3>')    // Headers (again for nested)
            .replace(/\*\* (.*?)(?=<br>|$)/g, '<li><strong>$1</strong></li>')  // Bold list items
            .replace(/^\d+\.\s\*\*(.*?)\*\*/gm, '<li><strong>$1</strong></li>')  // Numbered bold items
            .replace(/^\d+\.\s(.*?)(?=<br>|$)/gm, '<li>$1</li>')  // Numbered list items
            .replace(/^\*\s(.*?)(?=<br>|$)/gm, '<li>$1</li>')     // Bullet list items
            .replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');         // Wrap lists in ul tags
        
        // Debug: Log URLs found in the text
        const urlMatches = text.match(/(https?:\/\/(?:www\.)?[^\s<>"']+)/g);
        if (urlMatches) {
            console.log('Found URLs in text:', urlMatches);
        }
        
        // Also log the original text to see what the AI is generating
        console.log('Original text from AI:', text);
        
        let messageContent = `<b>${sender === 'user' ? 'You' : 'Assistant'}:</b> ` + formattedText;
        
        // Add product images if available
        if (productImages && productImages.length > 0) {
            messageContent += '<div class="product-images">';
            productImages.forEach(product => {
                if (product.img_url) {
                    messageContent += `
                        <div class="product-image-container">
                            <img src="${product.img_url}" alt="${product.name}" class="product-image" 
                                 onclick="window.open('${product.url}', '_blank')" 
                                 title="Click to view product">
                            <div class="product-name">${product.name}</div>
                        </div>
                    `;
                }
            });
            messageContent += '</div>';
        }
        
        div.innerHTML = messageContent;
        chat.appendChild(div);
        
        // Smart scroll: only auto-scroll if user is already near the bottom
        const isNearBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 100;
        if (isNearBottom) {
            chat.scrollTop = chat.scrollHeight;
        } else {
            // Show a subtle indicator that there's new content
            const scrollIndicator = document.getElementById('scroll-indicator');
            if (!scrollIndicator) {
                const indicator = document.createElement('div');
                indicator.id = 'scroll-indicator';
                indicator.innerHTML = '↓ New message';
                indicator.style.cssText = 'position: fixed; bottom: 80px; right: 20px; background: #1a73e8; color: white; padding: 8px 12px; border-radius: 20px; font-size: 12px; cursor: pointer; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.2);';
                indicator.onclick = () => {
                    chat.scrollTop = chat.scrollHeight;
                    indicator.remove();
                };
                document.body.appendChild(indicator);
                
                // Auto-remove indicator after 5 seconds
                setTimeout(() => {
                    if (indicator.parentNode) {
                        indicator.remove();
                    }
                }, 5000);
            }
        }
        
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
        
        // Only auto-scroll for typing indicator if user is near bottom
        const isNearBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 100;
        if (isNearBottom) {
            chat.scrollTop = chat.scrollHeight;
        }
        
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
            appendMessage('bot', reply, data.product_images || []);
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