import subprocess, numpy as np, json, sys
W,H,Y0=1920,220,860
p=subprocess.Popen(["ffmpeg","-v","error","-i","intro.mp4","-vf",f"crop={W}:{H}:0:{Y0}","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
box=np.array([11,16,26])
res=[]
i=0
while True:
    b=p.stdout.read(W*H*3)
    if len(b)<W*H*3: break
    a=np.frombuffer(b,np.uint8).reshape(H,W,3).astype(int)
    m=(np.abs(a-box).max(axis=2)<=7)
    rows=m.sum(axis=1); cols=m.sum(axis=0)
    r=np.where(rows>150)[0]
    if len(r)==0: res.append(None)
    else:
        y0,y1=r.min(),r.max()
        sub=m[y0:y1+1]
        c=np.where(sub.sum(axis=0)>(y1-y0)*0.3)[0]
        x0,x1=(int(c.min()),int(c.max())) if len(c) else (0,0)
        # text color: bright pixels inside box
        inner=a[y0:y1+1,x0:x1+1].reshape(-1,3)
        br=inner[inner.sum(axis=1)>450]
        col=[int(v) for v in np.median(br,axis=0)] if len(br) else None
        # signature: text pixel count
        res.append([int(y0+Y0),int(y1+Y0),x0,x1,col,int(len(br))])
    i+=1
json.dump(res,open("det.json","w"))
print(i)
