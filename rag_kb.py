import json
import requests
from dotenv import load_dotenv
import os

load_dotenv()
BUPT_API_KEY = os.getenv("BUPT_API_KEY")
BUPT_BASE_URL = os.getenv("BUPT_BASE_URL")
CHAT_MODEL = os.getenv("BUPT_CHAT_MODEL")

CARD_FILE = "pragmatic_cards.json"

def get_relevance_score(query: str, card: dict) -> int:
    # 适配你现在的json字段
    dialogue_text = "\n".join([f"{d['speaker']}：{d['text']}" for d in card["dialogue"]])
    card_text = (
        f"场景：{card['scene']}，目标短语：{card['target_phrase']}，"
        f"意图：{card['intent']}，备选表达：{card['alternative']}，对话：{dialogue_text}"
    )
    prompt = f"""
你现在是打分器，只输出0-100之间的数字，不要多余文字。
用户提问：{query}
待判断卡片内容：{card_text}
判断这条卡片和用户提问的语义相关程度：
100=完全匹配语境，0=完全无关
只返回数字！
"""
    headers = {
        "Authorization": f"Bearer {BUPT_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": CHAT_MODEL,
        "messages": [{"role":"user", "content": prompt}],
        "temperature": 0.1
    }
    resp = requests.post(f"{BUPT_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    try:
        score = int(content)
    except:
        score = 0
    return score

def load_cards() -> list[dict]:
    with open(CARD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def retrieve_top_k(query: str, k: int = 3) -> list[dict]:
    cards = load_cards()
    scored = []
    for card in cards:
        score = get_relevance_score(query, card)
        scored.append((score, card))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:k]]

if __name__ == "__main__":
    test_query = "这个词在朋友闲聊的时候是什么意思"
    res = retrieve_top_k(test_query, k=3)
    print(json.dumps(res, ensure_ascii=False, indent=2))
