# agent/seed_knowledge.py
"""One-shot script: seed initial audit rules into ChromaDB."""
from agent.knowledge_base import kb

RULES = [
    {
        "entity": "forbidden-words",
        "fact": "Document must not contain: 绝绝子, 无语子, 集美, 拴Q, yyds, emo, 破防了, 芭比Q了, 凡尔赛, 内卷",
    },
    {
        "entity": "format-standard",
        "fact": "Formal document titles must use size-2 Song font (二号宋体), body text size-3 FangSong (三号仿宋), line spacing 28pt",
    },
    {
        "entity": "data-privacy",
        "fact": "PII must be masked: phone middle-4 digits replaced with ****, ID card keeps first-6 and last-4 only",
    },
    {
        "entity": "citation-rule",
        "fact": "Quoted content must include source attribution: author, title, publish year, page number",
    },
    {
        "entity": "timeliness",
        "fact": "Regulatory references must be the latest version; repealed regulations cannot be cited as authority",
    },
    {
        "entity": "conflict-of-interest",
        "fact": "Author must proactively declare any conflicts of interest; concealment is prohibited",
    },
]

if __name__ == "__main__":
    print(f"Before: {kb.count()} entries")
    kb.ingest_rules(RULES)
    print(f"After:  {kb.count()} entries")
    print("Seed data loaded.")
