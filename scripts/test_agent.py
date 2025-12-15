"""
Quick test script for agent functionality
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent_graph import create_agent


def main():
    """Run quick tests"""
    print("🚀 Testing LangGraph ReAct Agent\n")
    
    agent = create_agent()
    
    test_queries = [
        "Xin chào!",
        "Tính 25 * 4",
        "Giải thích ReAct pattern là gì?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"❓ User: {query}")
        print(f"{'='*60}")
        
        try:
            result = agent.invoke(query)
            print(f"\n🤖 Agent: {result['response'][:200]}...")
            print(f"\n📊 Stats:")
            print(f"  - Iterations: {result.get('iterations', 0)}")
            print(f"  - Tools used: {result.get('tools_used', [])}")
            print(f"  - Success: {result.get('success', False)}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    print("\n\n✅ Test completed!")


if __name__ == "__main__":
    main()
