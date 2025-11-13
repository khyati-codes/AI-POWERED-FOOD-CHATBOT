# streamlit_foodie_bot.py

import streamlit as st
from openai import OpenAI
import json
import csv
import os
from dotenv import load_dotenv, dotenv_values

# ===================================================
# ✅ Load API key safely from your .env file only
# ===================================================

# Remove any globally set API key from system/user environment
os.environ.pop("OPENAI_API_KEY", None)

# Load your .env file explicitly
load_dotenv(dotenv_path=r"C:\Users\DeLL\Desktop\python\.env", override=True)

# Print API key and .env details (for debugging)
api_key = os.getenv("OPENAI_API_KEY")
print("✅ Loaded API key from .env:", api_key)
print("📁 .env file contents:", dotenv_values(r"C:\Users\DeLL\Desktop\python\.env"))

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# ===================================================
# 🍕 MENU
# ===================================================
MENU = {
    "pizza": 150,
    "burger": 100,
    "pasta": 120,
    "fries": 80,
    "coke": 50,
}

# ===================================================
# ⚙️ Helper Functions
# ===================================================

def parse_order_with_gpt(user_text):
    """
    Use GPT to extract food items and their quantities from the user's message.
    """
    prompt = f"""
    You are a food order parser.
    Extract the food items and their quantities from the user's message.
    Menu items: {list(MENU.keys())}
    Use this JSON format: {{"item": quantity, ...}}
    If a quantity isn't specified, assume 1.
    User message: "{user_text}"
    Only include valid menu items from the menu.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # you can also use gpt-4-turbo
        messages=[
            {"role": "system", "content": "You are a helpful food order assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    text = response.choices[0].message.content.strip()
    try:
        order_dict = json.loads(text)
        return order_dict
    except Exception:
        return {}

def save_order_to_csv(name, order, total):
    """
    Save user orders to a CSV file for record keeping.
    """
    with open("orders.csv", mode="a", newline="") as f:
        writer = csv.writer(f)
        for item, qty in order.items():
            writer.writerow([name, item, qty, MENU[item], MENU[item]*qty, total])

def show_bill(order):
    total = 0
    bill_summary = []
    for item, qty in order.items():
        if item in MENU:
            price = MENU[item] * qty
            bill_summary.append(f"{item.title()} x{qty} = ₹{price}")
            total += price
    return bill_summary, total

# ===================================================
# 💬 Streamlit Interface
# ===================================================

st.set_page_config(page_title="🍕 FoodieBot - AI Food Ordering Assistant", page_icon="🍔", layout="centered")

st.title("🍕 FoodieBot — AI Food Ordering Chatbot")
st.markdown("### Order your favorite food here!")

# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "order" not in st.session_state:
    st.session_state.order = {}

# Ask for user's name
#if "name" not in st.session_state:
 #   st.session_state.name = st.text_input("👋 What’s your name?")
  #  if not st.session_state.name:
   #     st.stop()
# Ask user name only once, and continue after input
# Ask user name only once, and continue after input
if "name" not in st.session_state or not st.session_state.name:
    name_input = st.text_input("👋 What’s your name?")
    if name_input:
        st.session_state.name = name_input.strip()
        st.rerun()  # rerun the app to show the chat UI
    st.stop()



st.markdown(f"Hello, **{st.session_state.name.title()}**! What would you like to order today?")

# Show previous chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if user_input := st.chat_input("Say or type your order..."):
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Parse order using GPT
    order_dict = parse_order_with_gpt(user_input)
    if order_dict:
        # Add parsed items to current order
        for item, qty in order_dict.items():
            if item in MENU:
                st.session_state.order[item] = st.session_state.order.get(item, 0) + int(qty)

        # Confirmation message
        with st.chat_message("assistant"):
            st.markdown("✅ Got it! I’ve added the following to your order:")
            for item, qty in order_dict.items():
                st.markdown(f"- {item.title()} x{qty}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "✅ Got it! I’ve added your items: " + str(order_dict)
            })
    else:
        with st.chat_message("assistant"):
            st.markdown("❌ Sorry, I didn’t catch that. Please mention valid items from the menu.")
        st.session_state.messages.append({
            "role": "assistant",
            "content": "❌ Sorry, I didn’t catch that. Please mention valid items from the menu."
        })

# ===================================================
# 🧾 Order Summary Section
# ===================================================
st.divider()
st.markdown("### 🧾 Current Order Summary")

if st.session_state.order:
    bill_summary, total = show_bill(st.session_state.order)
    for line in bill_summary:
        st.markdown(f"- {line}")
    st.markdown(f"**Total: ₹{total}**")

    confirm = st.button("✅ Confirm Order")
    cancel = st.button("❌ Cancel Order")

    if confirm:
        save_order_to_csv(st.session_state.name, st.session_state.order, total)
        st.success(f"🎉 Thank you {st.session_state.name.title()}! Your order (₹{total}) has been confirmed.")
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"🎉 Thank you {st.session_state.name.title()}! Your order for ₹{total} has been confirmed."
        })
        st.session_state.order = {}

    elif cancel:
        st.warning("Order cancelled. You can start a new one anytime!")
        st.session_state.order = {}
else:
    st.info("No items in your order yet. Start by typing or saying something like 'I want 2 pizzas and 1 coke' 🍕🥤")

# ===================================================
# 👣 Footer
# ===================================================
st.markdown("---")
#st.caption("Built with ❤️ using Streamlit + GPT-4o-mini")
