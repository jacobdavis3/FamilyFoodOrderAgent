#!/usr/bin/env python3
"""
Simple web interface for testing the food ordering agent
"""

from flask import Flask, render_template, request, jsonify, session
import json
import os
from food_bot import FoodOrderAgent, parse_message_with_llm
import asyncio
import threading

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Global agent instance
agent = FoodOrderAgent()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/process_message', methods=['POST'])
def process_message():
    """Process a message and return the agent's response"""
    data = request.get_json()
    message = data.get('message', '')
    user = data.get('user', 'Anonymous')
    
    if not message:
        return jsonify({'error': 'No message provided'})
    
    try:
        # Parse the message
        parsed = parse_message_with_llm(message)
        intent = parsed.get("intent")
        restaurant = parsed.get("restaurant")
        items = parsed.get("items", [])
        location = parsed.get("location")
        
        response = {
            'message': message,
            'user': user,
            'parsed': parsed,
            'response': '',
            'success': True
        }
        '''
        if intent == "RESTAURANT":
            if restaurant:
                # Search for restaurant (run async function in sync context)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    restaurant_info = loop.run_until_complete(search_restaurant(restaurant, location))
                    
                    if restaurant_info.get("found"):
                        agent.set_restaurant(restaurant_info)
                        response['response'] = (
                            f"✅ Found {restaurant_info['name']}!\n"
                            f"🌐 Ordering URL: {restaurant_info['url']}\n"
                            f"📋 Type: {restaurant_info['type']}"
                        )
                    else:
                        response['response'] = f"❌ Could not find ordering information for {restaurant}"
                finally:
                    loop.close()
            else:
                response['response'] = "❗ I couldn't identify a restaurant in your message."
        '''
        if intent == "ORDER":
            if items:
                agent.add_order(user, items)
                response['response'] = f"✅ Added {', '.join(items)} to {user}'s order."
            else:
                response['response'] = "❗ I couldn't find any food item in your message."
        
        elif intent == "QUERY":
            summary = agent.get_summary()
            response['response'] = summary
        
        elif intent == "PLACE_ORDER":
            if not agent.restaurant_info:
                response['response'] = "🚫 No restaurant selected. Please specify a restaurant first."
            else:
                response['response'] = "🚚 Starting order placement..."
                
                # Place the order (run async function in sync context)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(place_order(agent.restaurant_info, agent.orders))
                    
                    if result["success"]:
                        response['response'] = f"✅ {result['message']}"
                        if result.get('screenshot'):
                            response['screenshot'] = True
                    else:
                        response['response'] = f"❌ Order failed: {result['error']}"
                finally:
                    loop.close()
        
        else:
            response['response'] = (
                "🤖 I'm not sure what you meant. Try:\n"
                "- 'Let's order from Papa John's' (specify restaurant)\n"
                "- 'I want a large pepperoni pizza' (add food items)\n"
                "- 'What's our order?' (check order)\n"
                "- 'Place the order' (complete order)"
            )
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        })

@app.route('/api/get_status')
def get_status():
    """Get current order status"""
    try:
        summary = agent.get_summary()
        return jsonify({
            'summary': summary,
            'restaurant': agent.restaurant_info,
            'orders': agent.orders,
            'status': agent.order_status
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/clear_orders')
def clear_orders():
    """Clear all orders"""
    try:
        agent.orders = {}
        agent.restaurant_info = None
        agent.order_status = "collecting"
        return jsonify({'success': True, 'message': 'Orders cleared'})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create the HTML template
    html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Food Ordering Agent</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .chat-container {
            height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            margin-bottom: 20px;
            background-color: #fafafa;
        }
        .message {
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 5px;
        }
        .user-message {
            background-color: #e3f2fd;
            margin-left: 20%;
        }
        .agent-message {
            background-color: #f1f8e9;
            margin-right: 20%;
        }
        .input-container {
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        button {
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #45a049;
        }
        .status {
            margin-top: 20px;
            padding: 10px;
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
        }
        .controls {
            margin-top: 20px;
            display: flex;
            gap: 10px;
        }
        .controls button {
            background-color: #6c757d;
        }
        .controls button:hover {
            background-color: #5a6268;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🍕 Food Ordering Agent</h1>
        
        <div class="chat-container" id="chatContainer">
            <div class="message agent-message">
                🤖 Hello! I'm your food ordering assistant. I can help you:
                <ul>
                    <li>Find restaurants and their ordering links</li>
                    <li>Collect food orders from your group</li>
                    <li>Place orders automatically</li>
                </ul>
                Try saying: "Let's order from Papa John's" or "I want a large pepperoni pizza"
            </div>
        </div>
        
        <div class="input-container">
            <input type="text" id="messageInput" placeholder="Type your message here..." onkeypress="handleKeyPress(event)">
            <button onclick="sendMessage()">Send</button>
        </div>
        
        <div class="controls">
            <button onclick="getStatus()">📊 Check Status</button>
            <button onclick="clearOrders()">🗑️ Clear Orders</button>
        </div>
        
        <div class="status" id="status" style="display: none;"></div>
    </div>

    <script>
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessage(message, 'user');
            input.value = '';
            
            // Send to server
            fetch('/api/process_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    user: 'User'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addMessage(data.response, 'agent');
                } else {
                    addMessage('❌ Error: ' + data.error, 'agent');
                }
            })
            .catch(error => {
                addMessage('❌ Network error: ' + error, 'agent');
            });
        }

        function addMessage(text, sender) {
            const container = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}-message`;
            messageDiv.textContent = text;
            container.appendChild(messageDiv);
            container.scrollTop = container.scrollHeight;
        }

        function getStatus() {
            fetch('/api/get_status')
            .then(response => response.json())
            .then(data => {
                const statusDiv = document.getElementById('status');
                statusDiv.style.display = 'block';
                statusDiv.innerHTML = `
                    <h3>Current Status:</h3>
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                `;
            })
            .catch(error => {
                console.error('Error getting status:', error);
            });
        }

        function clearOrders() {
            fetch('/api/clear_orders')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addMessage('🗑️ Orders cleared!', 'agent');
                } else {
                    addMessage('❌ Error clearing orders: ' + data.error, 'agent');
                }
            })
            .catch(error => {
                addMessage('❌ Network error: ' + error, 'agent');
            });
        }
    </script>
</body>
</html>
    '''
    
    # Write the template file
    with open('templates/index.html', 'w') as f:
        f.write(html_template)
    
    print("🌐 Starting web interface on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000) 