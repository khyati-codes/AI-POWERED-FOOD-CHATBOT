# hybrid_food_chatbot.py

import time
import speech_recognition as sr
import pyttsx3
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import json
import csv
import os
import pandas as pd

# === Load environment variables ===
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === MENU ===
MENU = {
    "pizza": 150,
    "burger": 100,
    "pasta": 120,
    "fries": 80,
    "coke": 50,
    "coffee": 90,
    "sandwich": 110
}

# === FUNCTIONS ===
def parse_order_with_gpt(user_text):
    prompt = f"""
    Extract food items and quantities from this message.
    Menu: {list(MENU.keys())}
    Format JSON like this: {{"item": quantity}}
    Assume 1 if no quantity is given.
    User message: "{user_text}"
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a food order parser for a hotel restaurant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    try:
        order_dict = json.loads(response.choices[0].message.content.strip())
        return order_dict
    except:
        return {}

def save_order_to_csv(name, order, total):
    file_exists = os.path.isfile("orders.csv")
    with open("orders.csv", mode="a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Customer Name", "Item", "Quantity", "Price per Item", "Subtotal", "Total Bill"])
        for item, qty in order.items():
            writer.writerow([name, item, qty, MENU[item], MENU[item]*qty, total])

def show_bill(order):
    total = 0
    bill_summary = []
    for item, qty in order.items():
        if item in MENU:
            price = MENU[item] * qty
            bill_summary.append(f"{item.title()} × {qty} = ₹{price}")
            total += price
    return bill_summary, total

# === PAGE CONFIG ===
st.set_page_config(page_title="SkyView FoodieBot", page_icon="🍽️", layout="wide")

# === STYLING ===
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #f3f5f7 0%, #eef1f5 100%);
        }
        .header {
            background: linear-gradient(90deg, #004aad, #00b4db);
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            color: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            margin-bottom: 1rem;
        }
        .chat-bubble-user {
            background-color: #dcf8c6;
            padding: 0.8rem;
            border-radius: 10px;
            margin: 5px 0;
            text-align: right;
            color: #222;
        }
        .chat-bubble-bot {
            background-color: #f1f0f0;
            padding: 0.8rem;
            border-radius: 10px;
            margin: 5px 0;
            text-align: left;
            color: #333;
        }
        .bill-card {
            background-color: white;
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# === HEADER ===
st.markdown("""
<div class="header">
    <h1>🌇 SkyView FoodieBot</h1>
    <h3>Order delicious food with AI-powered assistance 🍕🥤</h3>
</div>
""", unsafe_allow_html=True)

# === SIDEBAR ===
st.sidebar.title("🏨 Sky View Hotel")
st.sidebar.image("https://images.unsplash.com/photo-1604147706283-7cc5f6c0f51d", use_container_width=True)
st.sidebar.caption("Luxury | Comfort | Taste")

menu_choice = st.sidebar.radio("Navigation", ["🍴 Customer Mode", "📊 Admin Dashboard"])

st.sidebar.markdown("---")
st.sidebar.subheader("Menu:")
for item, price in MENU.items():
    st.sidebar.markdown(f"- {item.title()} — ₹{price}")
st.sidebar.markdown("---")
st.sidebar.info("💡 Chat naturally to order — e.g. '2 pizzas and a coke please.'")

# === CUSTOMER MODE ===
if menu_choice == "🍴 Customer Mode":
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "order" not in st.session_state:
        st.session_state.order = {}

    # === ASK NAME ===
    if "name" not in st.session_state or not st.session_state.name:
        name_input = st.text_input("👋 Please enter your name to begin:")
        if name_input:
            st.session_state.name = name_input.strip()
            st.rerun()
        st.stop()

    st.markdown(f"### 👋 Hello, **{st.session_state.name.title()}!** What would you like to order today?")

    # === CHAT DISPLAY ===
    for msg in st.session_state.messages:
        bubble_class = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-bot"
        st.markdown(f'<div class="{bubble_class}">{msg["content"]}</div>', unsafe_allow_html=True)

    # === USER INPUT ===
    if user_input := st.chat_input("Type your order here..."):
        st.session_state.messages.append({"role": "user", "content": user_input})

        order_dict = parse_order_with_gpt(user_input)
        if order_dict:
            for item, qty in order_dict.items():
                if item in MENU:
                    st.session_state.order[item] = st.session_state.order.get(item, 0) + int(qty)

            added_items = ", ".join([f"{item.title()} x{qty}" for item, qty in order_dict.items()])
            response_text = f"✅ Got it! I've added: {added_items}"
            st.session_state.messages.append({"role": "assistant", "content": response_text})
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "❌ Sorry, I didn’t catch that. Please mention valid menu items."
            })

        st.rerun()

    # === BILL ===
    if st.session_state.order:
        st.markdown("<div class='bill-card'>", unsafe_allow_html=True)
        st.subheader("🧾 Current Order Summary")
        bill_summary, total = show_bill(st.session_state.order)
        for line in bill_summary:
            st.markdown(f"- {line}")
        st.markdown(f"**Total: ₹{total}**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm Order"):
                save_order_to_csv(st.session_state.name, st.session_state.order, total)
                st.success(f"🎉 Thank you {st.session_state.name.title()}! Your order for ₹{total} has been confirmed.")
                st.session_state.order = {}
        with col2:
            if st.button("❌ Cancel Order"):
                st.warning("Order cancelled.")
                st.session_state.order = {}
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No items yet — start by typing your order! 🍽️")

# === ADMIN DASHBOARD ===
elif menu_choice == "📊 Admin Dashboard":
    st.title("📊 Admin Dashboard - SkyView Orders")
    st.caption("Monitor all customer orders and total revenue.")

    if os.path.exists("orders.csv"):
        df = pd.read_csv("orders.csv")
        st.dataframe(df, use_container_width=True)

        # --- Filters ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filter Orders")
        names = df["Customer Name"].unique().tolist()
        name_filter = st.sidebar.selectbox("Filter by Customer", ["All"] + names)
        if name_filter != "All":
            df = df[df["Customer Name"] == name_filter]

        # --- Stats ---
        total_orders = len(df)
        total_sales = df["Total Bill"].sum() if "Total Bill" in df.columns else 0

        st.markdown(f"### 📦 Total Orders: {total_orders}")
        st.markdown(f"### 💰 Total Sales: ₹{total_sales}")
        st.bar_chart(df.groupby("Item")["Subtotal"].sum())

        # --- Download Option ---
        st.download_button(
            label="⬇️ Download Orders CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="SkyView_Orders_Report.csv",
            mime="text/csv"
        )
    else:
        st.warning("No orders found yet. Once customers order, data will appear here.")

st.markdown("---")
st.caption("💙 Built for Sky View Hotel | Powered by GPT-4o-mini + Streamlit")


# === Initialize Voice Engine ===
engine = pyttsx3.init()
engine.setProperty('rate', 170)
engine.setProperty('volume', 1.0)

def speak(text):
    """Speak and print text."""
    print(f"🤖 FoodieBot: {text}")
    engine.say(text)
    engine.runAndWait()

def listen():
    """Listen to user voice input."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎧 Listening... (or type below if you prefer)")
        audio = r.listen(source, phrase_time_limit=6)
    try:
        text = r.recognize_google(audio).lower()
        print(f"🗣️ You said: {text}")
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        speak("Speech service is not available right now.")
        return ""

def get_input(prompt=""):
    """Ask user for input - either voice or text."""
    speak(prompt)
    print("Type your answer OR speak it now 👇")
    voice_text = listen()
    if voice_text:
        return voice_text
    else:
        typed = input("⌨️ You: ").strip().lower()
        return typed

# === Menu & Order System ===
MENU = {
    "pizza": 150,
    "burger": 100,
    "pasta": 120,
    "fries": 80,
    "coke": 50,
}
order = {}

def show_menu():
    speak("Here’s our menu:")
    for item, price in MENU.items():
        speak(f"{item} for rupees {price}")

def take_order():
    while True:
        item = get_input("What would you like to order? Say or type 'done' to finish.")
        if "done" in item:
            break
        elif item not in MENU:
            speak("Sorry, we don’t have that item. Please choose from the menu.")
        else:
            qty_input = get_input(f"How many {item}s would you like?")
            try:
                qty = int(''.join(filter(str.isdigit, qty_input)) or 1)
            except ValueError:
                qty = 1
            order[item] = order.get(item, 0) + qty
            speak(f"Added {qty} {item}(s) to your order.")

def show_bill():
    total = 0
    speak("Here’s your order summary:")
    for item, qty in order.items():
        price = MENU[item] * qty
        speak(f"{item}, quantity {qty}, total rupees {price}")
        total += price
    speak(f"Your total amount is rupees {total}")
    return total

def chatbot():
    speak("Welcome to FoodieBot! Your voice and text-based food assistant.")
    name = get_input("May I know your name?")
    speak(f"Hello {name.title()}, nice to meet you! Let's start your order.")
    show_menu()
    take_order()

    if not order:
        speak("You didn’t order anything. Goodbye!")
        return

    total = show_bill()
    confirm = get_input("Would you like to confirm your order? Say yes or no.")
    if "yes" in confirm:
        speak(f"Thank you {name}! Your order for rupees {total} has been confirmed.")
    else:
        speak("Order cancelled. Hope to serve you next time!")

    speak("Goodbye and have a great day!")

if __name__ == "__main__":
    chatbot()
