from backend.app.core.conversation import Conversation


class ConversationManager:
    def __init__(self):
        self.conversations = {}

    def get(self, conversation_id: str):
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = Conversation(conversation_id)

        return self.conversations[conversation_id]


conversation_manager = ConversationManager()
