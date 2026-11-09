from clinic_assistant.chatbot.service import get_chat_response


message = "I have a headache and feel dizzy. What should I do?"

response = get_chat_response(message)

print("\nAI Response:")
print(response)