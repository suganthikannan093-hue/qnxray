import os, unittest
from qnxray.pidin import parse
from qnxray.mock import MockTarget
from qnxray.analyze import priority_inversions
FIX = os.path.join(os.path.dirname(__file__), "..", "..", "examples", "fixtures", "pidin_sample.txt")
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
