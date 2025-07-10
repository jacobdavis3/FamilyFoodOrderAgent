import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from openai import OpenAI
from telegram.request import HTTPXRequest




# -------------------- AGENT DEFINITION --------------------
class FoodOrderAgent:
    def __init__(self, model="gpt-4"):
        self.orders = {}  # Stores {username: [item1, item2, ...]}
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def process_message(self, user, message):
        message = message.strip().lower()

        if message == "summary":
            return self.summarize()

        elif message == "place order":
            return self.place_order()

        else:
            item = self.extract_food_item(message)
            if item:
                self.orders.setdefault(user, []).append(item)
                return f"✅ Added *{item}* to {user}'s order."
            else:
                return "❓ Sorry, I couldn't understand your order. Try again!"

    def extract_food_item(self, message):
        prompt = f"""Extract the food item(s) from this message in a short phrase.
Example: \"Can I get two tacos and a Coke?\" → \"two tacos and a Coke\"
Return only the item(s). Do not include extra words.

Message: \"{message}\"
Food item(s):"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            item = response.choices[0].message.content.strip()
            return item
        except Exception as e:
            print("OpenAI error:", e)
            return None

    def summarize(self):
        if not self.orders:
            return "📝 No orders yet."
        return "🧾 *Group Order Summary:*\n" + "\n".join(
            [f"- {user}: {', '.join(items)}" for user, items in self.orders.items()]
        )

    def place_order(self):
        if not self.orders:
            return "📭 No orders to place."
        summary = self.summarize()
        return f"🚚 *Placing order...*\n\n{summary}\n\n(You can integrate with an API here)"


# -------------------- TELEGRAM BOT SETUP --------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_FFBOT_KEY")
agent = FoodOrderAgent()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or update.effective_user.first_name
    message = update.message.text
    reply = agent.process_message(user, message)
    await update.message.reply_text(reply, parse_mode='Markdown')

if __name__ == '__main__':
    # Custom request with longer timeout
    custom_request = HTTPXRequest(connect_timeout=15.0, read_timeout=15.0)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).request(custom_request).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()