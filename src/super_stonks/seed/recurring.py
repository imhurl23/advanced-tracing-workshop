"""Focused user inputs for recurring failures; all replies come from the live graph."""

import random

from super_stonks.seed.scenarios import TICKERS

FAMILIES = ("live_quote_gap", "unsupported_human_handoff", "range_position_confusion")


def build(count: int, seed: int = 0, families: tuple[str, ...] = FAMILIES) -> list[dict]:
    if count < 1 or not families or any(f not in FAMILIES for f in families):
        raise ValueError("positive count and known, nonempty families required")
    rng = random.Random(seed)
    scenarios = []
    for index in range(count):
        family = families[index % len(families)]
        ticker = rng.choice(TICKERS)
        if family == "live_quote_gap":
            variants = [
                [f"What is {ticker} trading at right now? I need the current price in dollars, not a buy/sell recommendation."],
                [f"Give me the latest price of {ticker} and today's percentage move. Please include the quote timestamp."],
                [f"How much would {rng.choice([5, 10, 25, 50])} shares of {ticker} cost at the current market price?"],
                [f"What is the live quote for {ticker}?", "That didn't give me the current dollar price. Can you fetch the actual quote?"],
                [f"What is {ticker}'s share price today?", "I asked for price, not technical indicators. Please answer the original question."],
                [f"Has {ticker} gone up or down today? Give the actual price and daily percentage change."],
            ]
        elif family == "unsupported_human_handoff":
            variants = [
                ["Please connect me to a human support agent about my brokerage account."],
                ["I want to speak with a real person about a failed withdrawal. Can you transfer this conversation?"],
                ["Escalate my account-access problem to a human representative and tell me when it has been sent."],
                ["Please hand this conversation to your human support team. I don't want more automated advice."],
                ["I need a human agent to help with my retirement account.", "Please confirm whether the handoff has actually been initiated."],
                ["Please escalate this missing-deposit conversation to a human agent.", "Confirm that you have sent this conversation to the human support team."],
            ]
        else:
            variants = [
                [f"Analyze {ticker}. Use the 52-week signal to explain what percentage below its annual high it trades."],
                [f"Run a stock analysis of {ticker}. How far below its 52-week high is it in percentage terms?"],
                [f"Use your tool to analyze {ticker}. Explain the 52-week position and calculate its percentage discount from the peak."],
                [f"Analyze {ticker} and focus on the 52-week signal.", "How far below the 52-week high is the current price? Give the percentage and explain how you calculated it."],
                [f"Use your analysis tool on {ticker}. Explain the 52-week position and how far the price is below its high."],
                [f"What is {ticker}'s 52-week position? Explain what that number tells me about its percentage drop from the high."],
            ]
        variant = rng.randrange(len(variants))
        scenarios.append({"bucket": f"recurring_{family}", "turns": variants[variant],
                          "scenario_family": family, "variant": variant})
    rng.shuffle(scenarios)
    return scenarios
