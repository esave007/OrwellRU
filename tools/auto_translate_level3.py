#!/usr/bin/env python3
"""
Auto-translate pattern-based strings from level3:
- Social counters (N likes, N re-blabbers, etc.)
- Dates (April X, 2017 etc.)
- "read more" links
- "Joined: DATE"
- Posted timestamps
- User timestamps (Name (Date):)
"""
import json, re, sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Projects/OrwellRU/originals/level3_clean_strings.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Month translation map
MONTHS = {
    'January': 'января', 'February': 'февраля', 'March': 'марта',
    'April': 'апреля', 'May': 'мая', 'June': 'июня',
    'July': 'июля', 'August': 'августа', 'September': 'сентября',
    'October': 'октября', 'November': 'ноября', 'December': 'декабря',
    'Jan': 'янв.', 'Feb': 'фев.', 'Mar': 'мар.',
    'Apr': 'апр.', 'Jun': 'июн.', 'Jul': 'июл.',
    'Aug': 'авг.', 'Sep': 'сен.', 'Oct': 'окт.',
    'Nov': 'нояб.', 'Dec': 'дек.',
}

MONTHS_STANDALONE = {
    'January': 'Январь', 'February': 'Февраль', 'March': 'Март',
    'April': 'Апрель', 'May': 'Май', 'June': 'Июнь',
    'July': 'Июль', 'August': 'Август', 'September': 'Сентябрь',
    'October': 'Октябрь', 'November': 'Ноябрь', 'December': 'Декабрь',
}

DAYS = {
    'Monday': 'понедельник', 'Tuesday': 'вторник', 'Wednesday': 'среда',
    'Thursday': 'четверг', 'Friday': 'пятница', 'Saturday': 'суббота',
    'Sunday': 'воскресенье',
}

# Counter words (default forms, overridden by ru_plural for numbered counters)
COUNTER_WORDS = {
    'likes': 'отметок «Нравится»', 'like': 'отметка «Нравится»',
    're-blabbers': 'переблаблов', 're-blabber': 'переблабл',
    'comments': 'комментариев', 'comment': 'комментарий',
    'answers': 'ответов', 'answer': 'ответ',
    'upvotes': 'голосов', 'upvote': 'голос',
}

# Russian pluralization helper (approximate)
def ru_plural(n, word_key):
    """Simple Russian plural for counter words."""
    n = int(n)
    base_forms = {
        'likes': ('отметка «Нравится»', 'отметки «Нравится»', 'отметок «Нравится»'),
        'like': ('отметка «Нравится»', 'отметки «Нравится»', 'отметок «Нравится»'),
        're-blabbers': ('переблабл', 'переблабла', 'переблаблов'),
        're-blabber': ('переблабл', 'переблабла', 'переблаблов'),
        'comments': ('комментарий', 'комментария', 'комментариев'),
        'comment': ('комментарий', 'комментария', 'комментариев'),
        'answers': ('ответ', 'ответа', 'ответов'),
        'answer': ('ответ', 'ответа', 'ответов'),
        'upvotes': ('голос', 'голоса', 'голосов'),
        'upvote': ('голос', 'голоса', 'голосов'),
    }
    if word_key not in base_forms:
        return COUNTER_WORDS.get(word_key, word_key)

    one, few, many = base_forms[word_key]
    last2 = n % 100
    last1 = n % 10
    if 11 <= last2 <= 19:
        return many
    if last1 == 1:
        return one
    if 2 <= last1 <= 4:
        return few
    return many


def translate_date_inline(text):
    """Translate 'Month DD, YYYY' to 'DD месяца YYYY'."""
    # "April 14, 2017" -> "14 апреля 2017 г." (per Orwell 1 glossary)
    m = re.match(r'^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s*(\d{4})$', text.strip())
    if m:
        month, day, year = m.group(1), m.group(2), m.group(3)
        return f"{day} {MONTHS[month]} {year} г."

    # "April 14" -> "14 апреля"
    m = re.match(r'^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})$', text.strip())
    if m:
        month, day = m.group(1), m.group(2)
        return f"{day} {MONTHS[month]}"

    # Standalone month
    if text.strip() in MONTHS_STANDALONE:
        return MONTHS_STANDALONE[text.strip()]

    return None


def auto_translate(text):
    """Try to auto-translate a string. Returns None if can't."""
    t = text.strip()

    # Counter: "N word(s)"
    m = re.match(r'^(\d+)\s+(likes?|re-blabbers?|comments?|answers?|upvotes?)$', t, re.I)
    if m:
        num, word = m.group(1), m.group(2).lower()
        ru_word = ru_plural(int(num), word)
        return f"{num} {ru_word}"

    # "N comments, viewed M times"
    m = re.match(r'^(\d+)\s+comments?,\s+viewed\s+(\d+)\s+times?$', t)
    if m:
        comments, views = m.group(1), m.group(2)
        c_word = ru_plural(int(comments), 'comments')
        return f"{comments} {c_word}, {views} просмотров"

    # Simple date
    result = translate_date_inline(t)
    if result:
        return result

    # "Joined: DATE" — date_part already includes "г." if year present
    m = re.match(r'^Joined:\s+(.+)$', t)
    if m:
        date_part = translate_date_inline(m.group(1))
        if date_part:
            return f"Регистрация: {date_part}"

    # Posted timestamps: "Posted Day, Month DD, YYYY, HH:MM am/pm"
    m = re.match(r'^Posted\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4}),\s+(\d{1,2}):(\d{2})\s*(am|pm)$', t, re.I)
    if m:
        day_name, month, day, year, hour, minute, ampm = m.groups()
        ru_day = DAYS[day_name]
        ru_month = MONTHS[month]
        h = int(hour)
        if ampm.lower() == 'pm' and h != 12:
            h += 12
        elif ampm.lower() == 'am' and h == 12:
            h = 0
        return f"Опубликовано: {ru_day}, {day} {ru_month} {year} г., {h:02d}:{minute}"

    # <link...>read more</link>
    m = re.match(r'^(<link="[^"]*"><[^>]*>)read more(</color></link>)$', t)
    if m:
        return f"{m.group(1)}читать далее{m.group(2)}"

    return None


# Process all strings
translations = {}
auto_count = 0
for entry in data:
    text = entry['text']
    result = auto_translate(text)
    if result and result != text:
        translations[text] = result
        auto_count += 1

print(f"Auto-translated: {auto_count} strings")

# Show some examples
for i, (k, v) in enumerate(translations.items()):
    if i >= 30:
        break
    print(f"  {k[:60]:60s} -> {v[:60]}")

# Save as batch
with open('C:/Projects/OrwellRU/translated/batch_level3_auto.json', 'w', encoding='utf-8') as f:
    json.dump(translations, f, ensure_ascii=False, indent=2)
print(f"\nSaved batch_level3_auto.json with {len(translations)} entries")
