"""Extract the intro video from the game / put the re-rendered one back.

  intro_io.py extract <Ignorance_Data> intro.mp4
  intro_io.py install <Ignorance_Data> intro_ru.mp4

The clip "Orwell 2 Intro Final" lives in sharedassets2.resource (offset 0, whole file);
sharedassets2.assets stores its size (VideoClip.m_ExternalResources.m_Size). That value always
equals the size of the currently installed .resource file, so it is found and patched in place.
"""
import os, struct, sys, shutil


def main(cmd, data_dir, mp4):
    res = os.path.join(data_dir, "sharedassets2.resource")
    assets = os.path.join(data_dir, "sharedassets2.assets")
    if cmd == "extract":
        shutil.copyfile(res, mp4)
        return
    raw = bytearray(open(assets, "rb").read())
    old = struct.pack("<Q", os.path.getsize(res))
    assert raw.count(old) == 1, "clip size field not found exactly once"
    i = raw.find(old)
    raw[i:i + 8] = struct.pack("<Q", os.path.getsize(mp4))
    shutil.copyfile(mp4, res)
    open(assets, "wb").write(raw)
    print("installed", os.path.getsize(mp4), "bytes")


if __name__ == "__main__":
    main(*sys.argv[1:4])
