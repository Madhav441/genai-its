# utils/format_quiz_context.py

def format_quiz_context(q):
    """Format a quiz question/context dict for markdown display (for both ingestion and student views)."""
    import re
    context = q.get('context', '').strip()
    question = q.get('question', '').strip()
    # Use markdown for heading for Streamlit compatibility
    qnum = q.get('number', q.get('id', ''))
    if qnum:
        question_md = f"### **Question {qnum}**\n\n**{question}**"
    else:
        question_md = f"### **Question**\n\n**{question}**"
    def format_section_headers(text):
        # Highlight Sample/Expected Output sections with color and bold
        for section, color in [
            ("Sample Output:", "#FFD166"),
            ("Expected Output:", "#FFD166"),
            ("Instructions:", None),
            ("Context & Instructions:", None),
            ("Useful Functions:", None),
            ("Example code", None),
            ("Example Output", None),
            ("Requirements:", None),
            ("Data Structures:", None),
        ]:
            if color:
                text = re.sub(rf"(^|\n)\s*{re.escape(section)}", f"\n\n<span style='background-color:{color};color:#222;font-weight:bold;padding:2px 6px;border-radius:4px'>{section}</span>", text)
            else:
                text = re.sub(rf"(^|\n)\s*{re.escape(section)}", f"\n\n**{section}**", text)
        return text
    def bulletify_lines(text):
        lines = text.splitlines()
        new_lines = []
        for line in lines:
            l = line.strip()
            if (l and not l.startswith("**") and not l.startswith("```") and not l.startswith("#")
                and (l.startswith("-") or l.startswith("•") or re.match(r"^\d+\. ", l))):
                new_lines.append(line)
            elif l and not l.startswith("**") and not l.startswith("```") and not l.startswith("#") and not l.endswith(":"):
                new_lines.append(f"- {line.strip()}")
            else:
                new_lines.append(line)
        return "\n".join(new_lines)
    def highlight_numbers(text):
        # Only highlight numbers outside code blocks
        code_blocks = re.split(r'(```[\s\S]*?```)', text)
        for i in range(len(code_blocks)):
            if not code_blocks[i].startswith('```'):
                code_blocks[i] = re.sub(r"(\b\d+\b)", r"<span style='color:#F59E42'><b>\1</b></span>", code_blocks[i])
        return ''.join(code_blocks)
    def format_code_blocks(text):
        text = text.replace("```python", "\n```python").replace("```text", "\n```text").replace("```", "\n```")
        text = text.replace("\n```", "\n\n```")
        return text
    context_md = format_section_headers(context)
    context_md = bulletify_lines(context_md)
    context_md = highlight_numbers(context_md)
    context_md = format_code_blocks(context_md)
    return (
        f"{question_md}\n\n"
        f"**Context & Instructions:**\n\n{context_md}\n\n"
        f"<span style='color:#67D6FF'><b>Please type your answer below.</b></span>"
    )
