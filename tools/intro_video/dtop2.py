import subprocess, numpy as np, json
X0,Y0,W,H=560,380,800,300
p=subprocess.Popen(["ffmpeg","-v","error","-t","18.2","-i","intro.mp4","-vf",f"crop={W}:{H}:{X0}:{Y0}","-f","rawvideo","-pix_fmt","gray","-"],stdout=subprocess.PIPE)
out=[];i=0
while True:
    b=p.stdout.read(W*H)
    if len(b)<W*H: break
    a=np.frombuffer(b,np.uint8).reshape(H,W).astype(int)
    # local background: median of row → subtract to handle gradients
    bg=np.median(a,axis=1,keepdims=True)
    d=a-bg
    m=d>25
    rows=np.where(m.sum(axis=1)>3)[0]
    lines=[]
    if len(rows):
        start=rows[0];prev=rows[0]
        for r in list(rows[1:])+[10**9]:
            if r-prev>6:
                seg=m[start:prev+1]; xs=np.where(seg.any(axis=0))[0]
                lines.append([int(start+Y0),int(prev+Y0),int(xs.min()+X0),int(xs.max()+X0),int(d[start:prev+1].max()),int(seg.sum())])
                start=r
            prev=r
    out.append(lines); i+=1
json.dump(out,open("top.json","w"))
for i in list(range(15,50,3))+list(range(340,560,6)):
    print(i,f"{i/30:.2f}",out[i])
