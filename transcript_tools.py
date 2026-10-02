"""Impaginazione conservativa: cambia solo spazi e riferimenti temporali."""
import re


def readable_text(text, paragraph_chars=600):
    paragraphs = []
    for block in re.split(r'\n\s*\n', text.strip()):
        block = re.sub(r'\s+', ' ', block).strip()
        current = ''
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ0-9])', block):
            if current and len(current) + len(sentence) > paragraph_chars:
                paragraphs.append(current)
                current = ''
            current = (current + ' ' + sentence).strip()
        if current:
            paragraphs.append(current)
    return '\n\n'.join(paragraphs)


def timestamp(seconds):
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}' if hours else f'{minutes:02d}:{seconds:02d}'


def compose_transcript(segments):
    return '\n\n'.join(f"[{timestamp(item['start'])}] {readable_text(item['text'])}"
                       for item in segments if item['done'] and item['text'].strip())
