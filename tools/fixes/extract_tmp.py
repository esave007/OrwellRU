import sys, os, json, re, struct; sys.path.insert(0,".")
sys.stdout.reconfigure(encoding='utf-8')
from ttg import load
import UnityPy
src=sys.argv[1]; files=sys.argv[2:]
gg=UnityPy.load(os.path.join(src,"globalgamemanagers.assets"))
scripts={o.path_id:o.read_typetree()["m_ClassName"] for o in gg.objects if o.type.name=="MonoScript"}
CYR=re.compile("[А-Яа-яЁё]"); W=re.compile("[A-Za-z]{2,}")
res={}
for f in files:
    env=load(os.path.join(src,f)); sf=list(env.files.values())[0]
    out=[]
    for o in env.objects:
        if o.type.name!="MonoBehaviour": continue
        raw=o.get_raw_data(); fid,pid=struct.unpack_from("<iq",raw,16)
        cls=scripts.get(pid)
        if cls not in ("TextMeshProUGUI","TextMeshPro","Text"): continue
        t=o.read_typetree(); s=t.get("m_text") or t.get("m_Text") or ""
        go=t["m_GameObject"]["m_PathID"]
        if s.strip() and not CYR.search(s) and W.search(s):
            name=""
            try: name=env.files[list(env.files)[0]].objects[go].peek_name()
            except Exception: pass
            out.append(dict(pid=o.path_id,go=name,text=s,enabled=t.get("m_Enabled")))
    res[f]=out
    print(f,len(out),flush=True)
json.dump(res,open("tmp_english.json","w",encoding="utf-8"),ensure_ascii=False,indent=0)
