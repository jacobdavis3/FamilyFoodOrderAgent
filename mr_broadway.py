import json
import asyncio
from playwright.async_api import async_playwright

SAUCE_URL = "https://www.getsauce.com/order/mr-broadway/menu"
ORDER_FILE = "order.json"

async def load_order(filename=ORDER_FILE):
    with open(filename, "r") as f:
        return json.load(f)

async def add_items_to_cart(page, order):
    for item in order:
        name = item["name"]
        quantity = item["quantity"]
        print(f"Adding {quantity} x {name} to cart...")
        try:
            # Wait for menu to load and find the item by name
            await page.wait_for_selector(f"text={name}", timeout=10000)
            item_card = await page.query_selector(f"text={name}")
            if not item_card:
                print(f"Could not find menu item: {name}")
                continue
            await item_card.click()
            await page.wait_for_timeout(1000)
            # Increase quantity if needed
            for _ in range(1, quantity):
                plus_btn = await page.query_selector("button[aria-label='Increase quantity']")
                if plus_btn:
                    await plus_btn.click()
                    await page.wait_for_timeout(300)
            # Add to cart
            add_btn = await page.query_selector("button:has-text('Add to Cart')")
            if add_btn:
                await add_btn.click()
                await page.wait_for_timeout(1000)
            else:
                print(f"Could not find 'Add to Cart' button for {name}")
            # Close modal if needed
            close_btn = await page.query_selector("button[aria-label='Close']")
            if close_btn:
                await close_btn.click()
                await page.wait_for_timeout(300)
        except Exception as e:
            print(f"Error adding {name}: {e}")
            continue

async def proceed_to_checkout(page, delivery_info):
    print("Proceeding to checkout...")
    # Open cart
    await page.wait_for_selector("button[aria-label*='Cart'], button[aria-label*='View cart']", timeout=10000)
    cart_btn = await page.query_selector("button[aria-label*='Cart'], button[aria-label*='View cart']")
    if cart_btn:
        await cart_btn.click()
        await page.wait_for_timeout(2000)
    # Click checkout
    checkout_btn = await page.query_selector("button:has-text('Checkout')")
    if checkout_btn:
        await checkout_btn.click()
        await page.wait_for_timeout(2000)
    # Try to fill delivery info (selectors may need adjustment)
    try:
        # Wait for form fields to appear
        await page.wait_for_timeout(2000)
        name_input = await page.query_selector("input[name='name']")
        address_input = await page.query_selector("input[name='address']")
        phone_input = await page.query_selector("input[name='phone']")
        if name_input:
            await name_input.fill(delivery_info["name"])
        if address_input:
            await address_input.fill(delivery_info["address"])
        if phone_input:
            await phone_input.fill(delivery_info["phone"])
        print("Filled delivery info. Please complete payment manually if required.")
    except Exception as e:
        print(f"Could not fill delivery info automatically: {e}")
        print("Please fill in the remaining details manually.")

async def main():
    order_data = await load_order()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible mode
        page = await browser.new_page()
        await page.goto(SAUCE_URL)
        await page.wait_for_timeout(5000)  # Wait for page to load
        await add_items_to_cart(page, order_data["order"])
        await proceed_to_checkout(page, order_data["delivery_info"])
        print("\nAutomation complete. Please review your cart and complete the order in the browser.")
        input("Press Enter to close the browser...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 