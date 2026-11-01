"""Fix 47: default language in languages.json.  usage: python3 test47.py <mmiLoader.py>"""
import sys, types, importlib.util, copy
sys.modules["indexer"] = types.SimpleNamespace(process_dir=lambda *a: None)
spec = importlib.util.spec_from_file_location("mmiLoader", sys.argv[1]); m = importlib.util.module_from_spec(spec)
sys.modules["mmiLoader"] = m; spec.loader.exec_module(m)
P = F = 0
def case(name, recs, want):
    global P, F
    r = copy.deepcopy(recs); m.mark_default_language(r)
    got = [x["codes"][0] for x in r if x.get("default")]
    ok = got == want; P += ok; F += not ok
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else f": got {got}, want {want}"))
ar = {"codes": ["ar"], "text": "Arabic", "rtl": True}
case("the .152 key: ar, eng(+en), mya -> eng", [ar, {"codes": ["eng", "en"]}, {"codes": ["mya", "my"]}], ["eng"])
case("en folder -> en", [ar, {"codes": ["en"]}], ["en"])
case("regional en-GB -> en-GB", [ar, {"codes": ["en-GB"]}], ["en-GB"])
case("upper-case EN -> EN", [ar, {"codes": ["EN"]}], ["EN"])
case("no English -> first (ar)", [ar, {"codes": ["mya", "my"]}], ["ar"])
case("en and eng both -> only one default (first)", [ar, {"codes": ["en"]}, {"codes": ["eng", "en"]}], ["en"])
case("not fooled by 'ben' (Bengali)", [ar, {"codes": ["ben", "bn"]}], ["ar"])
case("not fooled by 'enm'", [ar, {"codes": ["enm"]}], ["ar"])
r = []; m.mark_default_language(r); ok = r == []; P += ok; F += not ok
print(("  [PASS] " if ok else "  [FAIL] ") + "empty list: no error")
print(f"\nResults: {P} passed, {F} failed"); sys.exit(1 if F else 0)
