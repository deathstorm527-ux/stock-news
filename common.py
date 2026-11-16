def groq_models():
    try:
        r = requests.get("https://api.groq.com/openai/v1/models",
            headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]}, timeout=20)
        ids = [m["id"] for m in r.json()["data"]]
    except Exception as e:
        print("model list fail", e); return []
    bad = ("whisper", "guard", "tts", "playai", "orpheus", "embed", "safeguard")
    ids = [i for i in ids if not any(b in i for b in bad)]
    pref = ["gpt-oss-120b", "llama-3.3-70b", "llama-4", "kimi", "qwen", "gpt-oss-20b", "llama-3.1-8b"]
    def rank(i):
        for n, p in enumerate(pref):
            if p in i: return n
        return 99
    ids = sorted(ids, key=rank)[:5]
    print("models to try:", ids)
    return ids

def ai(prompt, js=False):
    for m in groq_models():
        for use_json in ((True, False) if js else (False,)):
            try:
                body = {"model": m, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
                if use_json: body["response_format"] = {"type": "json_object"}
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]}, json=body, timeout=90)
                if r.status_code == 200:
                    t = r.json()["choices"][0]["message"]["content"]
                    if js:
                        a, b = t.find("{"), t.rfind("}")
                        if a >= 0 and b > a: t = t[a:b+1]
                    return t
                print("AI", m, r.status_code, r.text[:200])
            except Exception as e: print("AI err", m, e)
    return None
