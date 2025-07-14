import os
import logging
import json
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from openai import OpenAI
from telegram.request import HTTPXRequest

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------- AGENT DEFINITION --------------------
# Order agent
class FoodOrderAgent:
    def __init__(self):
        self.orders = {}

    def add_order(self, user, items):
        if user not in self.orders:
            self.orders[user] = []
        self.orders[user].extend(items)

    def get_summary(self):
        if not self.orders:
            return "🚫 No items in order."

        summary_lines = ["🧾 *Group Order Summary:*"]
        for user, items in self.orders.items():
            summary_lines.append(f"- *{user}*:")
            for item in items:
                summary_lines.append(f"  • {item}")
            summary_lines.append("")  # blank line for spacing between users
        summary_lines.append("_(You can integrate with an API here)_")
        return "\n".join(summary_lines)

    def place_order(self):
        if not self.orders:
            return "🚫 No orders yet."

        summary_lines = ["🚚 *Placing order...*"]
        for user, items in self.orders.items():
            summary_lines.append(f"- *{user}*:")
            for item in items:
                summary_lines.append(f"  • {item}")
            summary_lines.append("")  # Space between users
        summary_lines.append("_(You can integrate with an API here)_")
        return "\n".join(summary_lines)


# -------------------- LLM Parsing --------------------
def parse_message_with_llm(message: str) -> dict:
    system_prompt = (
        "You are a food-ordering assistant in a group chat. "
        "Your job is to extract a user's intent and a clean list of food items, formatted for clarity.\n\n"
        "For each item, include quantity (if mentioned), size/modifiers (e.g., 'no onions', 'extra cheese'), and name.\n\n"
        "Your JSON output should have:\n"
        "  - 'intent': One of [ORDER, QUERY, PLACE_ORDER, UNKNOWN]\n"
        "  - 'items': A list of strings like '1 Large Pizza', '1 Burger -- no sauce', etc.\n\n"
        "Message: \"{message}\"\nReturn:"
    )

    user_prompt = f"Message: \"{message}\"\nReturn:"

    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    content = response.choices[0].message.content.strip()
    try:
        json_start = re.search(r"\{", content).start()
        parsed = json.loads(content[json_start:])
    except Exception:
        parsed = {"intent": "UNKNOWN", "items": []}

    return parsed


# -------------------- TELEGRAM BOT SETUP --------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_FFBOT_KEY")
# initialize the agent
agent = FoodOrderAgent()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user.first_name

    parsed = parse_message_with_llm(text)
    intent = parsed.get("intent")
    items = parsed.get("items", [])

    if intent == "ORDER":
        if items:
            agent.add_order(user, items)
            await update.message.reply_text(f"✅ Added {', '.join(items)} to {user}'s order.")
        else:
            await update.message.reply_text("❗ I couldn't find any food item in your message.")
    elif intent == "QUERY":
        summary = agent.get_summary()
        await update.message.reply_text(summary)
    elif intent == "PLACE_ORDER":
        receipt = agent.place_order()
        await update.message.reply_text(receipt)
    else:
        await update.message.reply_text("🤖 I'm not sure what you meant. Try saying something like 'get sushi' or 'what’s my order'.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_FFBOT_KEY")).build()

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()
