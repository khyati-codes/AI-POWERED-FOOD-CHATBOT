# streamlit_foodie_bot.py

import os
import json
import csv
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# -------------------------------
# 🌗 LIGHT / DARK MODE SYSTEM
# -------------------------------
import streamlit as st

# Initialize theme state
if "theme" not in st.session_state:
    st.session_state.theme = "light"

# Toggle switch
toggle = st.sidebar.toggle("🌗 Dark Mode", value=False)
st.session_state.theme = "dark" if toggle else "light"

# -------------------------------
# APPLY CSS THEMES
# -------------------------------

dark_css = """
<style>

    /* --- FULL SCREEN DARK MODE FIX --- */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #0E1117 !important;
        color: white !important;
    }

    /* main content container */
    section.main > div {
        background-color: #0E1117 !important;
        color: white !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1C1F26 !important;
        color: white !important;
    }

    /* All text */
    p, span, div, label, h1, h2, h3, h4, h5, h6 {
        color: white !important;
    }

    /* Cards */
    .bill-card {
        background-color: #1F2128 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        border: 1px solid #333 !important;
        color: white !important;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background-color: #1F2128 !important;
        color: white !important;
        border-radius: 14px !important;
        padding: 14px !important;
    }

    /* Input boxes */
    .stTextInput input, textarea, select,
    div[data-baseweb="select"] > div {
        background-color: #1F2128 !important;
        color: white !important;
        border-radius: 8px !important;
        border: 1px solid #3A3D44 !important;
    }

    /* Buttons */
    .stButton>button {
        background-color: #3B3F47 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #5A5F68 !important;
    }

    /* Alerts (success, warning, info) */
    [data-testid="stAlert"] {
        background-color: #1A1D23 !important;
        color: white !important;
        border-left: 5px solid #6366F1 !important;
    }

    /* Dropdown text */
    label[data-testid="stRadioLabel"] p {
        color: white !important;
    }

</style>
"""

light_css = """
<style>

    /* Main background */
    .stApp {
        background-color: #F7F7F7 !important;
        color: black !important;
    }

    html, body, p, span, div {
        color: black !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
    }

    .bill-card {
        background-color: white !important;
        padding: 20px !important;
        border-radius: 12px !important;
        border: 1px solid #DDD !important;
    }

    button[kind="primary"], .stButton>button {
        background-color: #FFFFFF !important;
        color: black !important;
        border-radius: 8px !important;
        border: 1px solid #CCC !important;
    }

    .stTextInput input, textarea, select {
        background-color: white !important;
        color: black !important;
        border-radius: 8px !important;
    }

</style>
"""

# Apply theme
if st.session_state.theme == "dark":
    st.markdown(dark_css, unsafe_allow_html=True)
else:
    st.markdown(light_css, unsafe_allow_html=True)



# --------------------------
# Load API key safely
# --------------------------
os.environ.pop("OPENAI_API_KEY", None)  # ensure process env not overriding .env

DOTENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=DOTENV_PATH, override=True)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found. Add it to .env in project folder.")

client = OpenAI(api_key=api_key)

# --------------------------
# Full Menu
# --------------------------
FULL_MENU = {
    "pizza": 150,
    "burger": 100,
    "pasta": 120,
    "fries": 80,
    "coke": 50,
    "coffee": 90,
    "sandwich": 110,
    "chicken burger": 180,
    "fish fry": 220,
    "egg roll": 90
}

NON_VEG_WORDS = ["chicken", "fish", "egg", "meat", "non-veg", "nonveg"]

# --------------------------
# Helper functions
# --------------------------
def get_filtered_menu(veg_pref):
    """Return vegetarian-only menu if veg_pref == 'veg', else full menu."""
    if veg_pref == "veg":
        return {k: v for k, v in FULL_MENU.items() if not any(w in k.lower() for w in NON_VEG_WORDS)}
    return FULL_MENU


def parse_order_with_gpt(user_text, active_menu_keys):
    """
    Use OpenAI to parse a natural-language order.
    Returns a dict mapping item (lowercase) -> quantity (int).
    """
    allowed_list = ", ".join(active_menu_keys)
    prompt = f"""
You are a food order parser. Extract ordered items and quantities as JSON.
Allowed items: {allowed_list}
Return only a JSON object with item names (as in allowed list) mapped to quantities.
If no quantity is given assume 1.
Example: {{"pizza": 2, "coke": 1}}
User message: "{user_text}"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        text = response.choices[0].message.content.strip()

        # Try parsing JSON directly; if model wrapped it, extract braces
        try:
            data = json.loads(text)
        except Exception:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                fragment = text[start:end]
                data = json.loads(fragment)
            else:
                return {}

        # Normalize keys to lowercase and ints for qty
        result = {}
        for k, v in data.items():
            key = k.lower()
            try:
                qty = int(v)
            except:
                # if model returned string like "two", fallback to 1
                try:
                    qty = int(float(v))
                except:
                    qty = 1
            result[key] = qty
        return result

    except Exception as e:
        # show a non-fatal message in app; return empty parse
        st.error(f"Order parsing failed: {e}")
        return {}


def save_order_to_csv(name, order, total, active_menu):
    """Append order lines to orders.csv. active_menu needed for prices."""
    file_exists = os.path.isfile("orders.csv")
    with open("orders.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Customer Name", "Item", "Quantity", "Price", "Subtotal", "Total Bill"])
        for item, qty in order.items():
            price = active_menu.get(item, 0)
            subtotal = price * qty
            writer.writerow([name, item, qty, price, subtotal, total])


def show_bill(order, active_menu):
    """Return (lines, total) for current order using active_menu prices."""
    total = 0
    bill_summary = []
    for item, qty in order.items():
        price = active_menu.get(item, 0)
        subtotal = price * qty
        bill_summary.append(f"{item.title()} × {qty} = ₹{subtotal}")
        total += subtotal
    return bill_summary, total


# --------------------------
# Image/GIF Fullscreen Popup (Cute Cartoon Celebration)
# --------------------------
def show_image_popup(title, subtitle="", gif_url=None, duration=5000):
    """
    Show a full-screen popup with a GIF and text.
    duration in milliseconds.
    """
    if not gif_url:
        gif_url = "https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif"

    html = f"""
    <div id="image-popup" style="
        position: fixed;
        inset: 0;
        width: 100vw;
        height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(0,0,0,0.72);
        z-index: 100000;
    ">
      <div style="
        width: min(760px, 92%);
        background: linear-gradient(180deg, #fff 0%, #fffbf2 100%);
        border-radius: 18px;
        padding: 22px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.4);
        text-align: center;
        animation: popupScale 450ms ease;
      ">
        <img src="{gif_url}" alt="celebration" style="max-width:320px; width:60%; height:auto; display:block; margin:0 auto 16px auto; border-radius:12px;" />
        <div style="font-size:28px; font-weight:700; color:#222; margin-bottom:8px;">{title}</div>
        <div style="font-size:16px; color:#444; margin-bottom:6px;">{subtitle}</div>
      </div>
    </div>

    <style>
    @keyframes popupScale {{
      0% {{ transform: scale(0.85); opacity: 0; }}
      100% {{ transform: scale(1); opacity: 1; }}
    }}
    </style>

    <script>
    (function() {{
      const duration = {duration};
      setTimeout(function() {{
        const popup = document.getElementById("image-popup");
        if (!popup) return;
        popup.style.transition = "opacity 0.9s ease";
        popup.style.opacity = 0;
        setTimeout(() => popup.remove(), 900);
      }}, duration);
    }})();
    </script>
    """
    st.markdown(html, unsafe_allow_html=True)


# --------------------------
# Streamlit UI / Styling
# --------------------------
st.set_page_config(page_title="SkyView FoodieBot", page_icon="🍽️", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #f3f5f7 0%, #eef1f5 100%);
}
.bill-card {
    background: white;
    padding: 1rem;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>🌇 SkyView FoodieBot</h1>", unsafe_allow_html=True)

# --------------------------
# Sidebar navigation (Option A per user)
# --------------------------
st.sidebar.title("🏨 Sky View Hotel")
menu_choice = st.sidebar.selectbox("Mode", ["🍴 Customer Mode", "👨‍🍳 Admin Mode"])

# --------------------------
# CUSTOMER MODE
# --------------------------
if menu_choice == "🍴 Customer Mode":

    # initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "order" not in st.session_state:
        st.session_state.order = {}
    if "name" not in st.session_state:
        st.session_state.name = None

    # Ask for name (only once)
    if not st.session_state.name:
        name_input = st.text_input("👋 Please enter your name to begin:")
        if name_input:
            st.session_state.name = name_input.strip()

            # Auto-detect Jain surname
            if "jain" in st.session_state.name.lower():
                st.session_state.veg_preference = "veg"
                st.session_state.is_jain = True
            else:
                st.session_state.veg_preference = "any"
                st.session_state.is_jain = False

            st.rerun()
        st.stop()

    # Greeting
    st.markdown(f"### 👋 Hello, **{st.session_state.name.title()}!**")

    if st.session_state.get("is_jain", False):
        st.success("🙏 Jain surname detected — Veg-only menu applied by default.")

    # Veg preference toggle (user can override)
    st.session_state.veg_preference = st.radio(
        "Select food preference:",
        ["veg", "any"],
        index=0 if st.session_state.veg_preference == "veg" else 1
    )

    # Determine active menu
    ACTIVE_MENU = get_filtered_menu(st.session_state.veg_preference)

    # Show active menu in sidebar
    st.sidebar.subheader("Active Menu")
    for item_name, price in ACTIVE_MENU.items():
        st.sidebar.write(f"- {item_name.title()} — ₹{price}")

    # Show chat messages (simple)
    for msg in st.session_state.messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Using chat_message if available; fallback to markdown
        try:
            st.chat_message(role).write(content)
        except Exception:
            st.markdown(f"**{role.title()}:** {content}")

    # Chat input
    if user_input := st.chat_input("Type your order (e.g., '2 pizzas and 1 coke')"):
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Parse order with GPT restricted to ACTIVE_MENU keys
        parsed_order = parse_order_with_gpt(user_input, list(ACTIVE_MENU.keys()))
        if parsed_order:
            added_items = []
            for item, qty in parsed_order.items():
                key = item.lower()
                if key in ACTIVE_MENU:
                    st.session_state.order[key] = st.session_state.order.get(key, 0) + int(qty)
                    added_items.append(f"{key.title()} × {qty}")
            if added_items:
                st.session_state.messages.append({"role": "assistant", "content": f"✅ Added: {', '.join(added_items)}"})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "❌ None of the parsed items matched the active menu."})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "❌ Sorry, I couldn't parse that. Try: 'I want 2 pizzas and 1 coke'."})

        st.rerun()

    # Order summary & billing
    if st.session_state.order:
        st.markdown("<div class='bill-card'>", unsafe_allow_html=True)
        st.subheader("🧾 Current Order Summary")

        bill_lines, total = show_bill(st.session_state.order, ACTIVE_MENU)
        for line in bill_lines:
            st.markdown(f"- {line}")
        st.markdown(f"**Total: ₹{total}**")

        col1, col2 = st.columns(2)

        # Confirm Order button
        with col1:
            if st.button("✅ Confirm Order"):
                # Save CSV using active menu for prices
                save_order_to_csv(st.session_state.name, st.session_state.order, total, ACTIVE_MENU)

                # Show cute cartoon GIF full-screen popup (celebration)
                show_image_popup(
                    title="🎉 Order Confirmed!",
                    subtitle="Your delicious meal is being prepared and will arrive soon.",
                    gif_url="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExcWQwcWh2dWZmaHk2MjM0OXJiYmIzNjNuNGN4d3U4N2E0YTZ4M2VlOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/pIj4Yg3dudUddwGbHO/giphy.gif",
                    duration=5000  # milliseconds
                )

                # Clear order so next order starts fresh
                st.session_state.order = {}
                # Stop further rendering so popup DOM remains briefly until JS removes it
                st.stop()

        # Cancel Order button
        with col2:
            if st.button("❌ Cancel Order"):
                st.warning("Order cancelled.")
                st.session_state.order = {}
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No items yet — start by typing your order! 🍽️")


# --------------------------
# ADMIN MODE
# --------------------------
elif menu_choice == "👨‍🍳 Admin Mode":

    st.title("👨‍🍳 Admin Dashboard — SkyView Orders")
    st.caption("Monitor all customer orders and total revenue.")

    if os.path.exists("orders.csv"):
        df = pd.read_csv("orders.csv")
        st.dataframe(df, use_container_width=True)

        st.sidebar.markdown("---")
        st.sidebar.subheader("Filters")
        names = ["All"] + df["Customer Name"].unique().tolist()
        selected = st.sidebar.selectbox("Filter by Customer", names)

        if selected != "All":
            df = df[df["Customer Name"] == selected]

        st.markdown(f"### 📦 Total Orders: {len(df)}")
        total_sales = df["Total Bill"].sum() if "Total Bill" in df.columns else 0
        st.markdown(f"### 💰 Total Sales: ₹{total_sales}")

        # Sales by item chart (if present)
        if "Item" in df.columns and "Subtotal" in df.columns:
            chart_df = df.groupby("Item")["Subtotal"].sum().reset_index().set_index("Item")
            st.bar_chart(chart_df)

        st.download_button(
            label="⬇️ Download Orders CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="SkyView_Orders_Report.csv",
            mime="text/csv"
        )
    else:
        st.warning("No orders stored yet.")

# End of file
