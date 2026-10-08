"""Voice-over word timings for the Russian text.

Podcasts (PodcastPlayButton.StartSubtitles) and phone calls (CallPresenter.AnimatePhoneCallText) reveal the
text word by word: word i appears at VoiceOverTimings[id][i] seconds (podcasts skip the pause tokens
"...", "--", "-" when counting). The table (VoiceOverTimingsCollectionObject in resources.assets) was
made for the English words, so with a translated text the words run out of sync with the voice.

retime() builds a table for the Russian words, anchored on sentences: when a paragraph has the same number
of sentences in both languages, every Russian sentence starts exactly when the English one starts and ends
when the next English one begins; inside a sentence the words are placed by their relative position
(in characters) and get the time the English speaker reaches that position. Paragraphs whose sentences do
not match are timed as a whole, and texts whose paragraphs do not match as one block.
"""
import bisect
import re

PAUSES = ("...", "--", "-")
TAG = re.compile(r"<[^>]+>")
SENTENCE_END = re.compile(r"[.!?…]+[\"»”)\]]*$")


def split_words(text, podcast):
    """[(char offset, paragraph, sentence in paragraph, counted)] for the words the game iterates over."""
    out = []
    pos = para = sent = 0
    for w in text.split(" "):
        core = w[2:] if podcast and (w.startswith("\n") or "\n\n" in w) else w
        counted = not (podcast and core in PAUSES)
        out.append([pos, para, sent, counted])
        pos += len(w) + 1
        if "\n" in w:
            para += 1
            sent = 0
        elif SENTENCE_END.search(w.strip()) and w.strip() not in PAUSES:
            sent += 1
    return out, pos


def _interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect.bisect_right(xs, x) - 1
    if xs[i + 1] == xs[i]:
        return ys[i]
    return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i])


def _counts(words):
    """paragraph -> number of sentences (sentences with words in them)"""
    c = {}
    for _, para, sent, _ in words:
        c[para] = max(c.get(para, 0), sent + 1)
    return c


def _keys(words, other_counts, own_counts, by_para):
    """group key of every word: (paragraph, sentence) where the sentence counts agree, else (paragraph,)"""
    out = []
    for _, para, sent, _ in words:
        if not by_para:
            out.append((0,))
        elif own_counts.get(para) == other_counts.get(para):
            out.append((para, sent))
        else:
            out.append((para,))
    return out


def _spans(words, keys, total):
    """group key -> (start offset, end offset)"""
    g = {}
    for k, (w, key) in enumerate(zip(words, keys)):
        nxt = words[k + 1][0] if k + 1 < len(words) else total
        s, e = g.get(key, (w[0], nxt))
        g[key] = (min(s, w[0]), max(e, nxt))
    return g


def retime(en_text, ru_text, times, podcast):
    """New timing list for ru_text, or None if there is nothing to time."""
    if not podcast:  # calls: the game splits the paragraph text after parsing the <d …> markup
        en_text, ru_text = TAG.sub("", en_text), TAG.sub("", ru_text)
    en, en_len = split_words(en_text, podcast)
    ru, ru_len = split_words(ru_text, podcast)
    if not times or not any(w[3] for w in ru):
        return None
    if 0 < sum(w[3] for w in en) - len(times) <= 2:
        # the table lacks the last word(s); the game falls back to a glyph delay there
        extra = sum(w[3] for w in en) - len(times)
        for w in reversed(en):
            if extra and w[3]:
                w[3] = False
                extra -= 1
    en_c = [w for w in en if w[3]]
    ru_c = [w for w in ru if w[3]]
    if len(en_c) != len(times):
        # English text and table disagree: spread the Russian words evenly over the table
        n = len(times)
        return [times[min(n - 1, int(j * n / len(ru_c)))] for j in range(len(ru_c))]
    gap = (times[-1] - times[0]) / max(1, len(times) - 1)
    end_time = times[-1] + gap

    en_counts, ru_counts = _counts(en), _counts(ru)
    by_para = len(en_counts) == len(ru_counts)
    en_keys = _keys(en, ru_counts, en_counts, by_para)
    ru_keys = _keys(ru, en_counts, ru_counts, by_para)
    en_span, ru_span = _spans(en, en_keys, en_len), _spans(ru, ru_keys, ru_len)

    # English reference points per group: fraction of the group -> time
    ref, order = {}, []
    ti = 0
    for w, key in zip(en, en_keys):
        if not w[3]:
            continue
        if key not in ref:
            ref[key] = ([], [])
            order.append(key)
        s, e = en_span[key]
        ref[key][0].append((w[0] - s) / max(1, e - s))
        ref[key][1].append(times[ti])
        ti += 1
    # every group ends where the next one starts (the end of the last group: one average word later)
    for i, key in enumerate(order):
        nxt = ref[order[i + 1]][1][0] if i + 1 < len(order) else end_time
        ref[key][0].append(1.0)
        ref[key][1].append(max(nxt, ref[key][1][-1]))

    out = []
    for w, key in zip(ru, ru_keys):
        if not w[3]:
            continue
        s, e = ru_span[key]
        if key not in ref:  # group without counted English words: the closest earlier group
            key = next((k for k in reversed(order) if k <= key), order[0])
        xs, ys = ref[key]
        out.append(_interp((w[0] - s) / max(1, e - s), xs, ys))
    for i in range(1, len(out)):  # never earlier than the previous word
        out[i] = max(out[i], out[i - 1])
    return out
