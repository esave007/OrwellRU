"""Voice-over word timings for the Russian text.

Podcasts (PodcastPlayButton.StartSubtitles) and phone calls (CallPresenter.AnimatePhoneCallText) reveal the
text word by word: word i appears at VoiceOverTimings[id][i] seconds (podcasts skip the pause tokens
"...", "--", "-" when counting). The table (VoiceOverTimingsCollectionObject in resources.assets) was
made for the English words, so with a translated text the words run out of sync with the voice.

retime() builds a table for the Russian words: the start of every Russian word is placed at the same
relative position (by characters) of its paragraph as in the English text and gets the time the English
speaker reaches that position (linear between the English word timings).
"""
import bisect
import re

PAUSES = ("...", "--", "-")
TAG = re.compile(r"<[^>]+>")


def split_words(text, podcast):
    """[(char offset, paragraph, counted)] for the words the game iterates over (split on ' ')."""
    out = []
    pos = para = 0
    for w in text.split(" "):
        core = w[2:] if podcast and (w.startswith("\n") or "\n\n" in w) else w
        counted = not (podcast and core in PAUSES)
        out.append((pos, para, counted))
        pos += len(w) + 1
        if "\n" in w:
            para += 1
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


def retime(en_text, ru_text, times, podcast):
    """New timing list for ru_text, or None if the English text does not match the table."""
    if not podcast:  # calls: the game splits the paragraph text after parsing the <d …> markup
        en_text, ru_text = TAG.sub("", en_text), TAG.sub("", ru_text)
    en, en_len = split_words(en_text, podcast)
    ru, ru_len = split_words(ru_text, podcast)
    en_c = [w for w in en if w[2]]
    ru_c = [w for w in ru if w[2]]
    if not times or not ru_c:
        return None
    if 0 < len(en_c) - len(times) <= 2:
        en_c = en_c[:len(times)]  # the table lacks the last word(s); the game falls back to a glyph delay
    if len(en_c) != len(times):
        # English text and table disagree: spread the Russian words evenly over the table
        n = len(times)
        return [times[min(n - 1, int(j * n / len(ru_c)))] for j in range(len(ru_c))]
    gap = (times[-1] - times[0]) / max(1, len(times) - 1)
    end_time = times[-1] + gap

    def groups(words, total):
        """paragraph -> (start offset, end offset)"""
        g = {}
        for k, (pos, para, _) in enumerate(words):
            nxt = words[k + 1][0] if k + 1 < len(words) else total
            s, e = g.get(para, (pos, nxt))
            g[para] = (min(s, pos), max(e, nxt))
        return g

    en_g, ru_g = groups(en, en_len), groups(ru, ru_len)
    by_para = len(en_g) == len(ru_g)
    # English reference points: (paragraph, fraction of paragraph) -> time
    ref = {}
    for (pos, para, _), t in zip(en_c, times):
        key = para if by_para else 0
        s, e = en_g[para] if by_para else (0, en_len)
        ref.setdefault(key, ([], []))
        ref[key][0].append((pos - s) / max(1, e - s))
        ref[key][1].append(t)
    keys = sorted(ref)
    # close every paragraph at the start of the next one (or after the last word)
    for i, k in enumerate(keys):
        nxt = ref[keys[i + 1]][1][0] if i + 1 < len(keys) else end_time
        ref[k][0].append(1.0)
        ref[k][1].append(max(nxt, ref[k][1][-1]))
    out = []
    for pos, para, _ in ru_c:
        key = para if by_para else 0
        if key not in ref:  # paragraph without counted English words
            key = max(k for k in keys if k <= key) if any(k <= key for k in keys) else keys[0]
        s, e = ru_g[para] if by_para else (0, ru_len)
        xs, ys = ref[key]
        out.append(_interp((pos - s) / max(1, e - s), xs, ys))
    for i in range(1, len(out)):  # never earlier than the previous word
        out[i] = max(out[i], out[i - 1])
    return out
