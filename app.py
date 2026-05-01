import streamlit as st
from rag import store_document, retrieve
from groq import Groq
import ast
import operator

# ------------------ CONFIG ------------------ #
st.set_page_config(page_title="AI Agent Assistant", layout="centered")
st.title("🤖 AI Agent Assistant")

# ------------------ PDF UPLOAD ------------------ #
st.sidebar.markdown("## 📄 Upload PDF")
uploaded_file = st.sidebar.file_uploader("Upload your file", type=["pdf"])

if uploaded_file:
    store_document(uploaded_file)
    st.sidebar.success("Document added!")

st.markdown("### 💡 Hey! Moroni here! How can I help you?")

# ------------------ API ------------------ #
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ------------------ SYSTEM PROMPT ------------------ #
SYSTEM_PROMPT = """
You are an intelligent AI agent.

You can:
- Solve math problems (CALC)
- Execute Python code (PYTHON)
- Answer questions using uploaded documents (RAG)
- Chat and explain concepts (CHAT)

Always choose the correct tool.
Be precise and structured.
"""

# ------------------ MEMORY ------------------ #
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

# ------------------ MODEL ------------------ #
model = st.sidebar.selectbox(
    "Choose Model",
    ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
)

# ------------------ SAFE CALCULATOR ------------------ #
operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow
}

def safe_eval(expr):
    def eval_node(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            return operators[type(node.op)](
                eval_node(node.left),
                eval_node(node.right)
            )
        else:
            raise Exception("Invalid expression")

    try:
        tree = ast.parse(expr, mode='eval')
        return str(eval_node(tree.body))
    except:
        return "Invalid math expression"

# ------------------ SAFE PYTHON TOOL ------------------ #
def python_tool(code):
    try:
        safe_builtins = {
            "print": print,
            "range": range,
            "len": len
        }

        local_vars = {}
        exec(code, {"__builtins__": safe_builtins}, local_vars)

        return str(local_vars) if local_vars else "Code executed successfully"

    except Exception as e:
        return str(e)

# ------------------ AGENT DECISION ------------------ #
def decide(user_input):
    prompt = f"""
You are an AI agent.

Decide the best tool.

Available tools:
1. CALC → math
2. PYTHON → code execution
3. RAG → questions about uploaded documents
4. CHAT → general explanation

Respond STRICTLY:
TYPE: <CALC | PYTHON | RAG | CHAT>
INPUT: <content>

User: {user_input}
"""

    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content.strip()

# ------------------ AGENT EXECUTION ------------------ #
def run_agent(user_input):
    decision = decide(user_input)

    try:
        lines = decision.split("\n")
        type_line = [l for l in lines if "TYPE:" in l][0]
        input_line = [l for l in lines if "INPUT:" in l][0]

        task_type = type_line.replace("TYPE:", "").strip()
        task_input = input_line.replace("INPUT:", "").strip()

    except:
        task_type = "CHAT"
        task_input = user_input

    # ------------------ CALC ------------------ #
    if task_type == "CALC":
        result = safe_eval(task_input)
        return f"🧮 Result: {result}"

    # ------------------ PYTHON ------------------ #
    elif task_type == "PYTHON":
        result = python_tool(task_input)
        return f"🐍 Output: {result}"

    # ------------------ RAG ------------------ #
    elif task_type == "RAG":
        context_chunks = retrieve(task_input)
        context = "\n".join(context_chunks)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Answer using context."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{task_input}"}
            ]
        )

        return response.choices[0].message.content

    # ------------------ CHAT ------------------ #
    else:
        response = client.chat.completions.create(
            model=model,
            messages=st.session_state.messages
        )

        return response.choices[0].message.content

# ------------------ UI ------------------ #
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

user_input = st.chat_input("Ask anything...")

if user_input:
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Thinking..."):
        reply = run_agent(user_input)

    st.chat_message("assistant").write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})