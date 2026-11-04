import json, os, unittest
from unittest import mock
from qnxray import explain as X
D = os.path.join(os.path.dirname(__file__), "..", "..", "examples", "fixtures")
SRC = os.path.join(os.path.dirname(__file__), "..", "..", "examples", "inversion", "main.c")

def fake(content, seen):
    def t(url, headers, body):
        seen.append(body); return {"choices": [{"message": {"content": json.dumps(content)}}]}
    return t

class AI(unittest.TestCase):
    """LLM is mocked; fixtures were captured live against the QNX 8.0 QEMU target."""
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"QNXRAY_LLM_KEY": "sk-test-SECRET123", "QNXRAY_LLM": ""}); self.env.start()
    def tearDown(self): self.env.stop()
    def test_crash_ai_and_no_secret_sent(self):
        rep = json.load(open(os.path.join(D, "ai_crash.json"))); rep.pop("explanation")
        rep["stderr"] = "token=sk-abcdefABCDEF1234567890"
        seen = []
        a = X.analyze(rep, transport=fake({"summary": "NULL deref", "root_cause": "s is NULL", "evidence": ["bt"],
                                          "qnx_fix": "check NULL", "patch": "", "confidence": "high"}, seen))
        self.assertEqual(a["mode"], "ai"); self.assertEqual(a["root_cause"], "s is NULL")
        sent = json.dumps(seen[0]["messages"])
        self.assertNotIn("SECRET123", sent); self.assertNotIn("sk-abcdef", sent)
        self.assertIn("read_sensor", sent)   # source context is sent
    def test_invalid_json_falls_back_offline(self):
        inv = json.load(open(os.path.join(D, "ai_inversion.json")))[0]; inv.pop("explanation")
        a = X.analyze(inv, transport=fake({"nope": 1}, []))
        self.assertEqual(a["mode"], "offline"); self.assertIn("ai_error", a)
    def test_inversion_evidence_chain(self):
        inv = json.load(open(os.path.join(D, "ai_inversion.json")))[0]
        ev = X.inversion_evidence(inv, None, {"duration_s": 1.0, "threads": {"1/1": {"REPLY": 1.0}}})
        self.assertEqual(ev["timeline"]["window_s"], 1.0)
        self.assertIn("waiter", json.dumps(ev))
    def test_offline_key_off(self):
        with mock.patch.dict(os.environ, {"QNXRAY_LLM": "off"}):
            inv = json.load(open(os.path.join(D, "ai_inversion.json")))[0]
            self.assertEqual(X.analyze(inv)["mode"], "offline")
    def test_fix_ai_edit_validated(self):
        src = open(SRC).read()
        good = {"qnx_fix": "drop flag", "edits": [{"find": "ChannelCreate(inherit ? 0 : _NTO_CHF_FIXED_PRIORITY)", "replace": "ChannelCreate(0)"}]}
        self.assertEqual(X.propose_fix({}, src, transport=fake(good, []))["mode"], "ai")
        bad = {"qnx_fix": "x", "edits": [{"find": "not in source", "replace": "y"}]}
        f = X.propose_fix({}, src, transport=fake(bad, []))
        self.assertEqual(f["mode"], "offline"); self.assertEqual(f["edits"][0]["replace"], "ChannelCreate(0)")
    def test_fix_rejects_patch_that_keeps_fixed_priority(self):
        src = open(SRC).read()
        sneaky = {"qnx_fix": "swap", "edits": [{"find": "inherit ? 0 : _NTO_CHF_FIXED_PRIORITY", "replace": "inherit ? _NTO_CHF_FIXED_PRIORITY : 0"}]}
        f = X.propose_fix({}, src, transport=fake(sneaky, []))
        self.assertEqual(f["mode"], "offline"); self.assertEqual(f["ai_error"], "ValueError")
    def test_live_fix_fixture(self):
        d = json.load(open(os.path.join(D, "ai_fix_verify.json")))
        self.assertEqual(d["status"], "verified"); self.assertLess(d["after_s"], 0.8); self.assertGreater(d["before_s"], 2.5)
        self.assertIn("-    int chid = ChannelCreate(inherit ? 0 : _NTO_CHF_FIXED_PRIORITY);", d["patch"])
