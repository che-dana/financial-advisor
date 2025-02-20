import openai
import streamlit as st
import os
import json
from dotenv import load_dotenv

# ---------------------------
# Load environment variables & API key
# ---------------------------
load_dotenv()
AZURE_OPENAI_ENDPOINT = st.secrets("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = st.secrets("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = st.secrets("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT_NAME = st.secrets("AZURE_OPENAI_DEPLOYMENT_NAME")  # Add this line
client = openai.AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        default_headers=None
    )

# ---------------------------
# Load Knowledge Base
# ---------------------------
def load_knowledge_base():
    """Load the knowledge base JSON file containing product details, historical performance, etc."""
    with open("knowledge_base.json", "r", encoding="utf-8") as file:
        return json.load(file)

knowledge_base = load_knowledge_base()

# ---------------------------
# Initialize OpenAI Client
# ---------------------------
client = openai.AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION
)

# ---------------------------
# Streamlit Config
# ---------------------------
st.set_page_config(page_title="DANA Financial Sales Assistant", page_icon="💰", layout="wide")

# ---------------------------
# SIDEBAR: User Profile & Investment Options
# ---------------------------
st.sidebar.markdown("### 🔹 User Profile")
openness = st.sidebar.selectbox("Openness", ["High", "Low"])
conscientiousness = st.sidebar.selectbox("Conscientiousness", ["High", "Low"])
extraversion = st.sidebar.selectbox("Extraversion", ["High", "Low"])
agreeableness = st.sidebar.selectbox("Agreeableness", ["High", "Low"])
neuroticism = st.sidebar.selectbox("Neuroticism", ["High", "Low"])

education_level = st.sidebar.selectbox("Education Level", ["High School", "Bachelor's", "Master's", "PhD"])
income_level = st.sidebar.selectbox("Income Level", ["Low", "Medium", "High"])
housing_status = st.sidebar.selectbox("Housing Status", ["Renting", "Own House", "Living with Family"])
vehicle_ownership = st.sidebar.selectbox("Vehicle Ownership", ["None", "Car", "Motorcycle"])
nature_of_work = st.sidebar.selectbox("Nature of Work", ["Salaried", "Self-employed", "Freelancer", "Retired"])
family_dependants = st.sidebar.number_input("Number of Family Dependants", min_value=0, max_value=10, value=1)
age = st.sidebar.slider("Age", min_value=18, max_value=100, value=30)
behavioral = st.sidebar.selectbox("Behavioral Trait", ["Saver", "Spender", "Investor"])

st.sidebar.markdown("### 💰 Investment Products")
# Limit to only these three products (keys in our knowledge base)
investment_options = {
    key: st.sidebar.radio(f"Existing {key} User?", ["No", "Yes"])
    for key in ["DANA+", "Reksadana", "eMAS"]
}

# ---------------------------
# 1) FIRST PROMPT: Generate Marketing Plan
# ---------------------------
def generate_marketing_plan():
    """
    Creates a personalized marketing plan including:
    - Best suited products (limited to DANA+, Reksadana, and eMAS)
    - Best marketing technique (selected from a provided list)
    - A persuasive conversation starter
    - A full conversation sequence to pursue the user to invest
    """
    # Updated marketing techniques list (with duplicates as provided)
    marketing_techniques = [
        "Curiosity gap", "Creative storytelling", "Sensory appeal",
        "Curiosity gap", "Creative storytelling", "Sensory appeal",
        "Social proof with emphasis on familiarity", "Authority and expertise", "Risk aversion and safety",
        "Social proof with emphasis on familiarity", "Authority and expertise", "Risk aversion and safety",
        "Data-oriented messaging", "Commitment and consistency", "Delayed action",
        "Data-oriented messaging", "Commitment and consistency", "Delayed action",
        "Urgency", "Simplicity in choices", "Loss aversion",
        "Urgency", "Simplicity in choices", "Loss aversion",
        "Social proof", "Enthusiastic messaging", "Exciting storytelling",
        "Social proof", "Enthusiastic messaging", "Exciting storytelling",
        "Information-rich and thoughtful content", "Independence bias", "Privacy",
        "Information-rich and thoughtful content", "Independence bias", "Privacy",
        "Reciprocity", "Emotional appeals", "Inclusive social proof",
        "Reciprocity", "Emotional appeals", "Inclusive social proof",
        "Exclusivity", "Autonomy bias", "Straightforward and logical messaging",
        "Exclusivity", "Autonomy bias", "Straightforward and logical messaging",
        "Loss aversion with scarcity", "Curiosity gap with urgency", "Security & trust messaging",
        "Loss aversion with scarcity", "Curiosity gap with urgency", "Security & trust messaging",
        "Positive reinforcement", "Sustainable benefits", "Optimistic framing",
        "Positive reinforcement", "Sustainable benefits", "Optimistic framing"
    ]
    random_technique = marketing_techniques[hash(age + family_dependants) % len(marketing_techniques)]

    prompt = f"""
    You are an expert in marketing and psychology. Guide an online sales assistant to sell investment products to Dana Indonesia's e-wallet users over live chat.

    # User Profile:
    - Openness: {openness}, Conscientiousness: {conscientiousness}, Extraversion: {extraversion},
      Agreeableness: {agreeableness}, Neuroticism: {neuroticism}
    - Income Level: {income_level}
    - Behavioral: {behavioral}
    - Existing Investments: {json.dumps(investment_options)}

    # Generate:
    1. The best suited products (only DANA+, Reksadana, and eMAS) for this user.
    2. The best marketing technique → **({random_technique})**.
    3. A great conversation starter based on their emotional needs, e.g., "Have you ever wanted to save money without worrying about the ups and downs of the economy?"
    4. A step-by-step conversation sequence to pursue the user to invest.
    """

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT_NAME,  # Using the deployment name
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message.content

def generate_conversation_starter(marketing_plan_text: str) -> str:
    """
    Using the marketing plan, generate a persuasive conversation starter (<60 words)
    that is highly compelling and ends with a question.
    """
    prompt = f"""
    Based on the following marketing plan:
    {marketing_plan_text}

    Generate a persuasive conversation starter for an online live chat sales assistant for Dana Indonesia.
    The message must be less than 60 words and end with a question, making it difficult for users not to invest.
    """
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT_NAME,  # Using the deployment name
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message.content

# ---------------------------
# 2) SECOND PROMPT: Live Chat Assistant Handler
# ---------------------------
def handle_user_question(user_input: str) -> str:
    """
    Uses the pre-generated marketing plan and the knowledge base to generate a persuasive live chat response.
    The response must:
      - Be less than 60 words.
      - Suggest only DANA+, Reksadana, and eMAS.
      - Leverage historical growth data to compel the user.
      - End with a question.
    """
    marketing_plan = st.session_state.get("marketing_plan", "")
    if not marketing_plan:
        return "Please click 'Start Conversation' to begin."

    # We instruct the assistant to focus on the three products and use historical growth data persuasively.
    second_prompt = f"""
    You are an online live chat sales Assistant for Dana Indonesia.
    You speak in less than 60 words and only answer investment-related questions about DANA+, Reksadana, and eMAS.
    Your personality is that of a good relationship builder, curious, and mindful of user psychology.

    # Marketing Plan:
    {marketing_plan}

    # Knowledge Base (including historical performance and product details):
    {json.dumps(knowledge_base)}

    # User says:
    {user_input}

    Using the conversation sequence from the marketing plan, and emphasizing the impressive historical growth of the products, provide a persuasive answer that suggests only DANA+, Reksadana, or eMAS. End your response with a question to encourage the user to invest.
    """
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT_NAME,  # Changed from "gpt-4" to use Azure deployment name
        messages=[{"role": "system", "content": second_prompt}]
    )
    return response.choices[0].message.content

# ---------------------------
# Session Initialization
# ---------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "conversation_started" not in st.session_state:
    st.session_state["conversation_started"] = False

# ---------------------------
# SIDEBAR: Start Conversation Button (Single Instance)
# ---------------------------
st.sidebar.markdown("### 🚀 Start Conversation")
if st.sidebar.button("Start Conversation", use_container_width=True):
    st.session_state["messages"] = []
    # Generate marketing plan (first prompt)
    plan = generate_marketing_plan()
    st.session_state["marketing_plan"] = plan
    # Generate conversation starter (using marketing plan)
    conversation_starter = generate_conversation_starter(plan)
    st.session_state["messages"].append({"role": "assistant", "content": conversation_starter})
    st.session_state["conversation_started"] = True

# ---------------------------
# Display Chat History (Only user & assistant messages)
# ---------------------------
for message in st.session_state["messages"]:
    if message["role"] != "system":
        st.chat_message(message["role"]).write(message["content"])

# ---------------------------
# Chat Input (Live Chat using Second Prompt)
# ---------------------------
prompt = st.chat_input("Type your message here...")
if prompt:
    assistant_reply = handle_user_question(prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.session_state["messages"].append({"role": "assistant", "content": assistant_reply})
    st.chat_message("assistant").write(assistant_reply)
