"""Extract all TextLocalized strings (and their state) from game files -> loc_<file>.json"""
import sys, os, json, re, struct; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
from ttg import load
import UnityPy
src_dir=sys.argv[1]; files=sys.argv[2:]
gg=UnityPy.load(os.path.join(src_dir,"globalgamemanagers.assets"))
scripts={o.path_id:o.read_typetree()["m_ClassName"] for o in gg.objects if o.type.name=="MonoScript"}
CYR=re.compile("[А-Яа-яЁё]")
def walk(x,path):
    if isinstance(x,dict):
        if "_text" in x and isinstance(x["_text"],list) and all(isinstance(s,str) for s in x["_text"]):
            yield path+"._text", x["_text"]
        for k,v in x.items(): yield from walk(v,path+"."+k)
    elif isinstance(x,list):
        for i,v in enumerate(x):
            if isinstance(v,(dict,list)): yield from walk(v,f"{path}[{i}]")
for f in files:
    env=load(os.path.join(src_dir,f)); out=[]; bad=0
    for o in env.objects:
        if o.type.name!="MonoBehaviour": continue
        raw=o.get_raw_data()
        fid,pid=struct.unpack_from("<iq",raw,16)
        cls=scripts.get(pid) if fid in (0,1) else None
        if cls in ("TextMeshProUGUI","TextMeshPro","Image","RectTransform","CanvasScaler","GraphicRaycaster","LayoutElement","ContentSizeFitter","HorizontalLayoutGroup","VerticalLayoutGroup","Button","Mask","RectMask2D","CanvasGroup"): continue
        try: t=o.read_typetree()
        except Exception as e: bad+=1; continue
        for path,arr in walk(t,""):
            for i,s in enumerate(arr):
                if s.strip():
                    out.append(dict(pid=o.path_id,cls=cls,path=path,idx=i,text=s,ru=bool(CYR.search(s))))
    json.dump(out,open(f"loc_{f}.json","w",encoding="utf-8"),ensure_ascii=False,indent=0)
    n_en=sum(1 for x in out if not x["ru"]); print(f, "strings",len(out),"english",n_en,"parse errors",bad, flush=True)
