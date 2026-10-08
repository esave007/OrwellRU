"""UnityPy environment with MonoBehaviour typetrees generated from the game's assemblies."""
import os
import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
from UnityPy.helpers.TypeTreeNode import TypeTreeNode

G = os.environ.get("ORWELL_GAME", r"G:\Games\Steam\steamapps\common\Orwell Ignorance is Strength")
D = os.path.join(G, "Ignorance_Data")
DLLS = ["mscorlib.dll", "System.dll", "System.Core.dll", "System.Xml.dll", "UnityEngine.dll",
        "UnityEngine.UI.dll", "Assembly-CSharp-firstpass.dll", "Assembly-CSharp.dll",
        "SmartLocalization_Runtime.dll"]


class FixedGenerator(TypeTreeGenerator):
    """TypeTreeGeneratorAPI labels string[] fields as type 'string' (with an Array of strings
    inside). UnityPy then reads them as a single string and fails; relabel them as 'vector'."""

    def get_nodes_up(self, assembly, fullname):
        key = (assembly, fullname)
        if key in self.cache:
            return self.cache[key]
        if not assembly.endswith(".dll"):
            assembly = f"{assembly}.dll"
        base = list(self.get_nodes(assembly, fullname))
        types = [n.m_Type for n in base]
        for i, n in enumerate(base):
            if (n.m_Type == "string" and i + 3 < len(base) and base[i + 1].m_Type == "Array"
                    and base[i + 1].m_Level == n.m_Level + 1 and base[i + 3].m_Type != "char"):
                types[i] = "vector"
        node = TypeTreeNode.from_list([
            TypeTreeNode(b.m_Level, types[i], b.m_Name, 0, 0, m_MetaFlag=b.m_MetaFlag)
            for i, b in enumerate(base)])
        self.cache[key] = node
        return node


_G = None


def gen():
    global _G
    if _G:
        return _G
    g = FixedGenerator("5.6.3f1")
    for f in DLLS:
        g.load_dll(open(os.path.join(D, "Managed", f), "rb").read())
    _G = g
    return g


def load(path):
    env = UnityPy.load(path)
    env.typetree_generator = gen()
    return env
