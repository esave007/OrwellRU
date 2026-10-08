// Runtime layout fixes for the Russian translation of Orwell: Ignorance is Strength.
//
// The in-game websites/documents are laid out once in the editor for the English text: every
// text block, background image and data-chunk highlight box ("chunk box ... (Clone)") has a fixed
// position and size. Russian text is longer, so blocks overflow into each other and the highlight
// boxes stay where the English words used to be. This component (started from an injected call in
// TextMeshProUGUI.Awake, see inject.ps1) periodically checks the active TMP texts and
//   1. shrinks the font of Cyrillic texts that no longer fit their rect,
//   2. moves the chunk highlight boxes onto the actual position of the linked words, the same way
//      the game builds them at runtime (ChunkBoxDrawing.CreateBoxesForChunk / CreateBox),
//   3. translates captions the game fills with an enum name (ToString()): the Listener tab caption
//      (CommunicationType: Chat/Mail/Call), the Insider tab caption and the device headers in the
//      Insider bookmarks (InsiderDevice.DeviceType: PC/Notebook/Phone). The labels are found through the
//      fields of the components that own them.
// Everything is wrapped in try/catch: a failure is written to OrwellRuFix.log and never reaches the game.

using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace OrwellRuFix
{
    public static class Loader
    {
        static bool _started;

        public static void Init()
        {
            if (_started)
                return;
            _started = true;
            try
            {
                var go = new GameObject("OrwellRuFix");
                UnityEngine.Object.DontDestroyOnLoad(go);
                go.AddComponent<TextFixer>();
                Log.Write("started");
            }
            catch (Exception e)
            {
                Log.Write("init failed: " + e);
            }
        }
    }

    static class Log
    {
        static string _path;
        static int _lines;

        public static void Write(string s)
        {
            if (_lines++ > 2000)
                return;
            try
            {
                if (_path == null)
                    _path = Path.Combine(Path.GetDirectoryName(Application.dataPath), "OrwellRuFix.log");
                File.AppendAllText(_path, DateTime.Now.ToString("HH:mm:ss ") + s + "\n");
            }
            catch
            {
            }
        }
    }

    public class TextFixer : MonoBehaviour
    {
        const float ScanInterval = 0.25f;
        const float MinScale = 0.75f;

        class State
        {
            public int Signature;
            public float OriginalSize;
        }

        static readonly Dictionary<string, string> EnumCaptions = new Dictionary<string, string>
        {
            { "Chat", "Чат" }, { "Mail", "Почта" }, { "Call", "Звонок" },
            { "PC", "ПК" }, { "Notebook", "Ноутбук" }, { "Phone", "Телефон" },
        };

        // component type -> its TextMeshProUGUI field that receives the enum name
        static readonly KeyValuePair<Type, string>[] CaptionFields =
        {
            new KeyValuePair<Type, string>(typeof(Orwell.Applications.ListenerTabHeader), "_contentTabCaption"),
            new KeyValuePair<Type, string>(typeof(Orwell.Applications.InsiderTabHeader), "_contentTabCaption"),
            new KeyValuePair<Type, string>(typeof(InsiderDeviceHeader), "_nameLabel"),
        };

        static void TranslateEnumCaptions()
        {
            const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public;
            foreach (var cf in CaptionFields)
            {
                FieldInfo field = cf.Key.GetField(cf.Value, flags);
                if (field == null)
                    continue;
                foreach (UnityEngine.Object owner in FindObjectsOfType(cf.Key))
                {
                    var label = field.GetValue(owner) as TextMeshProUGUI;
                    string ru;
                    if (label != null && label.text != null && EnumCaptions.TryGetValue(label.text, out ru))
                        label.text = ru;
                }
            }
        }

        readonly Dictionary<int, State> _states = new Dictionary<int, State>();
        float _nextScan;

        void Update()
        {
            if (Time.unscaledTime < _nextScan)
                return;
            _nextScan = Time.unscaledTime + ScanInterval;
            try
            {
                TranslateEnumCaptions();
            }
            catch (Exception e)
            {
                Log.Write("captions failed: " + e.Message);
            }
            TextMeshProUGUI[] texts;
            try
            {
                texts = FindObjectsOfType<TextMeshProUGUI>();
            }
            catch (Exception e)
            {
                Log.Write("scan failed: " + e.Message);
                return;
            }
            for (int i = 0; i < texts.Length; i++)
            {
                try
                {
                    Process(texts[i]);
                }
                catch (Exception e)
                {
                    Log.Write("error on '" + texts[i].name + "': " + e);
                }
            }
        }

        void Process(TextMeshProUGUI t)
        {
            if (!t.isActiveAndEnabled)
                return;
            string text = t.text;
            if (string.IsNullOrEmpty(text))
                return;
            Rect r = t.rectTransform.rect;
            int id = t.GetInstanceID();
            State st;
            if (!_states.TryGetValue(id, out st))
            {
                st = new State { OriginalSize = t.fontSize };
                _states[id] = st;
            }
            int sig = text.GetHashCode() ^ ((int)(r.width * 8f) * 397) ^ ((int)(r.height * 8f) * 7919);
            if (sig == st.Signature)
                return;
            st.Signature = sig;

            if (HasCyrillic(text))
                Fit(t, st, r);
            FixChunkBoxes(t);
        }

        static bool HasCyrillic(string s)
        {
            for (int i = 0; i < s.Length; i++)
                if (s[i] >= 'Ѐ' && s[i] <= 'ӿ')
                    return true;
            return false;
        }

        // Texts that grow with their content (chat bubbles, layout groups) are left alone.
        static bool IsDynamic(TextMeshProUGUI t)
        {
            if (t.GetComponent<ContentSizeFitter>() != null || t.GetComponent<LayoutElement>() != null)
                return true;
            Transform p = t.transform.parent;
            if (p != null && (p.GetComponent<LayoutGroup>() != null || p.GetComponent<ContentSizeFitter>() != null))
                return true;
            return t.GetComponentInParent<Orwell.Documents.Chat>() != null;
        }

        static void Fit(TextMeshProUGUI t, State st, Rect r)
        {
            if (t.enableAutoSizing || r.width < 4f || r.height < 4f || IsDynamic(t))
                return;
            if (Mathf.Abs(t.fontSize - st.OriginalSize) > 0.01f)
                t.fontSize = st.OriginalSize;
            if (!Overflows(t, r, st.OriginalSize))
                return;
            float lo = st.OriginalSize * MinScale, hi = st.OriginalSize;
            for (int i = 0; i < 8; i++)
            {
                float mid = (lo + hi) * 0.5f;
                t.fontSize = mid;
                if (Overflows(t, r, st.OriginalSize))
                    hi = mid;
                else
                    lo = mid;
            }
            t.fontSize = lo;
            Log.Write(string.Format("fit '{0}' {1:0.#} -> {2:0.#}: {3}", t.name, st.OriginalSize, lo,
                Shorten(t.text)));
        }

        // Wrapped text: more than ~0.4 line taller than its rect. Single-line text: wider than its rect.
        static bool Overflows(TextMeshProUGUI t, Rect r, float originalSize)
        {
            Vector4 m = t.margin;
            float width = r.width - m.x - m.z;
            float height = r.height - m.y - m.w;
            if (t.enableWordWrapping)
            {
                Vector2 pv = t.GetPreferredValues(t.text, width, 0f);
                return pv.y > height + originalSize * 0.4f;
            }
            Vector2 one = t.GetPreferredValues(t.text, 0f, 0f);
            return one.x > width + 2f;
        }

        static string Shorten(string s)
        {
            s = s.Replace("\r", " ").Replace("\n", " ");
            return s.Length > 60 ? s.Substring(0, 60) + "..." : s;
        }

        // ---- data chunk highlight boxes -------------------------------------------------------

        static void FixChunkBoxes(TextMeshProUGUI t)
        {
            TextDataChunk[] chunks = t.GetComponents<TextDataChunk>();
            if (chunks.Length == 0 || t.GetComponentInParent<Orwell.Documents.Chat>() != null)
                return;
            t.ForceMeshUpdate();
            TMP_TextInfo ti = t.textInfo;
            for (int c = 0; c < chunks.Length; c++)
            {
                List<Selectable> boxes = chunks[c].BackgroundButtons;
                if (boxes == null || boxes.Count == 0 || boxes[0] == null)
                    continue;
                int link = FindLink(ti, chunks[c].Id);
                if (link < 0)
                    continue;
                List<Vector3[]> segments = LineSegments(t, ti, ti.linkInfo[link]);
                if (segments.Count == 0)
                    continue;
                while (boxes.Count < segments.Count)
                {
                    Selectable proto = boxes[boxes.Count - 1];
                    var clone = (Selectable)Instantiate(proto, proto.transform.parent);
                    clone.transform.SetSiblingIndex(proto.transform.GetSiblingIndex() + 1);
                    boxes.Add(clone);
                }
                for (int i = 0; i < boxes.Count; i++)
                {
                    if (boxes[i] == null)
                        continue;
                    var rt = (RectTransform)boxes[i].transform;
                    if (i < segments.Count)
                        Place(rt, segments[i][0], segments[i][1]);
                    else
                        rt.sizeDelta = Vector2.zero;
                }
            }
        }

        static int FindLink(TMP_TextInfo ti, string id)
        {
            if (string.IsNullOrEmpty(id))
                return -1;
            for (int i = 0; i < ti.linkCount; i++)
                if (ti.linkInfo[i].GetLinkID() == id)
                    return i;
            return -1;
        }

        // World-space (bottom-left, top-right) of the link text on every line it occupies, with the
        // same padding the game uses for non-chat boxes (5 left/right, 10 on top).
        static List<Vector3[]> LineSegments(TextMeshProUGUI t, TMP_TextInfo ti, TMP_LinkInfo li)
        {
            var result = new List<Vector3[]>();
            int line = -1;
            float x0 = 0f, x1 = 0f, top = float.MinValue, bottom = float.MaxValue;
            bool any = false;
            int end = Math.Min(li.linkTextfirstCharacterIndex + li.linkTextLength, ti.characterCount);
            for (int i = li.linkTextfirstCharacterIndex; i < end; i++)
            {
                TMP_CharacterInfo ci = ti.characterInfo[i];
                if (ci.lineNumber != line)
                {
                    if (any)
                        result.Add(Segment(t, x0, x1, top, bottom));
                    line = ci.lineNumber;
                    any = false;
                    top = float.MinValue;
                    bottom = float.MaxValue;
                }
                if (char.IsWhiteSpace(ci.character))
                    continue;
                if (!any)
                    x0 = ci.bottomLeft.x;
                any = true;
                x1 = ci.topRight.x;
                top = Mathf.Max(top, ci.ascender);
                bottom = Mathf.Min(bottom, ci.descender);
            }
            if (any)
                result.Add(Segment(t, x0, x1, top, bottom));
            return result;
        }

        static Vector3[] Segment(TextMeshProUGUI t, float x0, float x1, float top, float bottom)
        {
            Vector3 bl = t.transform.TransformPoint(new Vector3(x0, bottom, 0f));
            Vector3 tr = t.transform.TransformPoint(new Vector3(x1, top, 0f));
            bl.x -= 5f;
            tr.x += 5f;
            tr.y += 10f;
            return new[] { bl, tr };
        }

        static void Place(RectTransform rt, Vector3 worldBottomLeft, Vector3 worldTopRight)
        {
            Transform p = rt.parent;
            Vector3 bl = p != null ? p.InverseTransformPoint(worldBottomLeft) : worldBottomLeft;
            Vector3 tr = p != null ? p.InverseTransformPoint(worldTopRight) : worldTopRight;
            float w = tr.x - bl.x, h = tr.y - bl.y;
            if (rt.anchorMin != rt.anchorMax)
                rt.anchorMax = rt.anchorMin;
            Vector3 s = rt.localScale;
            rt.sizeDelta = new Vector2(s.x != 0f ? w / s.x : w, s.y != 0f ? h / s.y : h);
            rt.localPosition = new Vector3(bl.x + rt.pivot.x * w, bl.y + rt.pivot.y * h, rt.localPosition.z);
        }
    }
}
