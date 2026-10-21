
from langchain_groq import ChatGroq


def main():
    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0,
        max_tokens=150,
        max_retries=1,
    )

    response = llm.invoke(
        "In two short sentences, explain how an AI customer "
        "support agent can use knowledge-base articles to help a customer."
    )

    print("\nGroq API test successful!")
    print("Model: openai/gpt-oss-20b")
    print("\nModel response:")
    print(response.content)


if __name__ == "__main__":
    main()
