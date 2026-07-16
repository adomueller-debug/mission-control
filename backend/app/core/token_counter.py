class TokenCounter:
    def estimate(self, text: str):
        return max(1, len(text.split()))
