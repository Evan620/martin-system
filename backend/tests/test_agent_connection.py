from app.agents.supervisor import SupervisorAgent
from app.core.config import settings

def test_agent_hello():
    print(f"🤖 Testing Agent Connection to {settings.OLLAMA_BASE_URL}...")
    
    agent = SupervisorAgent()
    
    # Simple query to check if Brain is awake
    try:
        response = agent.smart_chat(
            message="Hello, are you online?"
        )
        print(f"✅ Agent Response: {response}")
    except Exception as e:
        print(f"❌ Agent Connection Failed: {e}")
        print("Tip: Ensure 'ollama serve' is running and model is pulled.")

if __name__ == "__main__":
    test_agent_hello()
