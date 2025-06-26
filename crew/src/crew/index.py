from cook_crew import CookCrew

def main():
    print("👩‍🍳 Welcome to the Cooking Assistant! Ask anything related to cooking or substitutions.\nType 'exit' to quit.\n")
    cook_crew = CookCrew()

    while True:
        query = input("📝 Your Question: ").strip()
        if query.lower() in ['exit', 'quit']:
            print("👋 Goodbye! Happy cooking!")
            break

        # Get the crew instance (no input parameter needed here)
        crew = cook_crew.cooking_crew()
        
        # Pass the query as inputs to kickoff method
        result = crew.kickoff(inputs={"user_query": query})
        
        print(f"\n🤖 Result:\n{result}")
        print("\n--- Ask another question or type 'exit' ---\n")

if __name__ == "__main__":
    main()
