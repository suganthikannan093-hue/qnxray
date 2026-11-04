import os, unittest
from qnxray.pidin import parse
from qnxray.mock import MockTarget
from qnxray.analyze import priority_inversions
FIX = os.path.join(os.path.dirname(__file__), "..", "..", "examples", "fixtures", "pidin_handwritten_inversion.txt")
D = os.path.join(os.path.dirname(__file__), "..", "..", "examples", "fixtures")
class Real(unittest.TestCase):
    """Fixtures captured from the QNX SDP 8.0 QEMU quickstart target."""
    def test_real_pidin(self):
        s = parse(open(os.path.join(D, "pidin_qnx800_qemu.txt")).read())
        self.assertGreater(len(s.processes), 20)
        k = s.processes[0]
        self.assertEqual(k.pid, 1); self.assertGreater(len(k.threads), 10)
        self.assertIn("INTR", {t.state for t in k.threads})
        self.assertIn("i", {t.policy for t in k.threads})
        self.assertTrue(any(p.name.endswith("io-sock") for p in s.processes))
        self.assertEqual(len({p.pid for p in s.processes}), len(s.processes))
    def test_real_agent_json(self):
        import json
        d = json.load(open(os.path.join(D, "agent_qnx800_qemu.json")))
        self.assertEqual(d["source"], "agent")
        self.assertTrue(all("threads" in p and p["threads"] for p in d["processes"]))
    def test_gdb_parse(self):
        from qnxray.target import parse_gdb
        r = parse_gdb(open(os.path.join(D, "gdb_crashy_core.txt")).read())
        self.assertEqual(r["signal"], "SIGSEGV")
        self.assertTrue(r["backtrace"][0].startswith("read_sensor"))
        self.assertEqual(len(r["backtrace"]), 2)
class Trace(unittest.TestCase):
    def test_inversion_timeline(self):
        from qnxray.trace import parse_traceprinter, build_timeline
        h, ev, names = parse_traceprinter(open(os.path.join(D, "inversion_traceprinter.txt")).read())
        self.assertEqual(h["TRACE_CPU_NUM"], "4")
        pids = {p for p, n in names.items() if "inversion" in n}
        self.assertEqual(len(pids), 3)
        tl = build_timeline(h, ev, names, pids)
        top = {k: max(v["states_s"], key=v["states_s"].get) for k, v in tl["threads"].items()}
        self.assertEqual(sorted(top.values()), ["READY", "REPLY", "RUNNING"])  # server starved, client stuck, hog runs
class Inv(unittest.TestCase):
    def test_preempted_by(self):
        from qnxray.model import Snapshot, Process, Thread
        s = Snapshot(0, "t", [Process(1, "srv", [Thread(1, "srv", 10, "f", "READY")]),
                              Process(2, "hog", [Thread(1, "hog", 20, "f", "RUNNING")]),
                              Process(3, "cli", [Thread(1, "cli", 30, "f", "REPLY", "1")])])
        i = priority_inversions(s)[0]
        self.assertEqual(i["severity"], "high"); self.assertIn("hog", i["preempted_by"][0])
        from qnxray.explain import offline
        self.assertIn("Priority inversion", offline(i))
class T(unittest.TestCase):
    def test_parse(self):
        s = parse(open(FIX).read())
        self.assertEqual([p.pid for p in s.processes], [1, 4100, 20500, 20501])
        sf = s.processes[2]
        self.assertEqual(len(sf.threads), 2)
        self.assertEqual(sf.threads[1].state, "MUTEX")
        self.assertEqual(sf.threads[0].policy, "f")
    def test_inversion(self):
        inv = priority_inversions(parse(open(FIX).read()))
        self.assertEqual(inv[0]["owner"], "./logger_lowprio")
    def test_mock(self):
        s = MockTarget(seed=1).snapshot()
        self.assertTrue(any(p.name == "io-sock" for p in s.processes))
if __name__ == "__main__":
    unittest.main()
