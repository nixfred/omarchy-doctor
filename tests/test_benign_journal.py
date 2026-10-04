import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import doctor

def probe(text="",code=0):
    return {"ok":code==0,"code":code,"stdout":text,"output":text,"command":"fake diagnostic"}

def journal(*entries):
    """Run Probes.journal() over fake journalctl JSON lines; each entry is a (identifier, message) pair."""
    lines='\n'.join(json.dumps({"SYSLOG_IDENTIFIER":i,"MESSAGE":m}) for i,m in entries)
    return doctor.Probes(lambda *a,**kw:probe(lines)).journal()

def matches(message):
    return [why for pattern,why in doctor.BENIGN_JOURNAL if re.search(pattern,message)]

# One realistic notice per BENIGN_JOURNAL entry (kernel, wpa_supplicant, bluetoothd, kernel) and
# near-misses that share a prefix, subsystem or device with it but are different failures.
CASES={
    "TDX":(
        "virt/tdx: TDX not supported by the host platform",
        ("virt/tdx: module initialization failed (-16)","virt/tdx: TDX not supported by the host kernel config","virt/sgx: SGX not supported by the host platform"),
    ),
    "nl80211 multicast":(
        "nl80211: kernel reports: multicast RX registrations are not supported",
        ("nl80211: kernel reports: Operation not supported","nl80211: kernel reports: Match already configured","nl80211: Failed to set channel (freq=5180): -16"),
    ),
    "bluez Host is down":(
        "profiles/audio/avdtp.c:avdtp_connect_cb() connect to 74:3F:8E:A5:5C:A1: Host is down (112)",
        ("profiles/audio/avdtp.c:avdtp_connect_cb() connect to 74:3F:8E:A5:5C:A1: Connection refused (111)",
         "profiles/audio/avdtp.c:avdtp_connect_cb() connect to 74:3F:8E:A5:5C:A1: Permission denied (13)",
         "profiles/audio/a2dp.c:a2dp_connect_cb() connect to 74:3F:8E:A5:5C:A1: Host is down (112)",
         "avdtp_connect_cb() connect to not-a-mac: Host is down (112)"),
    ),
    "ucsi GET_CURRENT_CAM":(
        "ucsi_acpi USBC000:00: GET_CURRENT_CAM command failed",
        ("ucsi_acpi USBC000:00: GET_CONNECTOR_STATUS failed (-5)","ucsi_acpi USBC000:00: GET_CAM_SUPPORTED command failed",
         "ucsi_acpi USBC000:00: unknown error 0","ucsi_acpi USBC000:00: GET_CURRENT_CAM timed out"),
    ),
}

class BenignJournalPatterns(unittest.TestCase):
    def test_every_pattern_has_a_case(self):
        # A new BENIGN_JOURNAL entry without a positive case here fails, so the list cannot grow untested.
        self.assertEqual(len(doctor.BENIGN_JOURNAL),len(CASES))
        for pattern,_ in doctor.BENIGN_JOURNAL:
            self.assertTrue(any(re.search(pattern,good) for good,_ in CASES.values()),pattern)

    def test_each_pattern_matches_its_real_notice_and_only_that_pattern(self):
        for name,(good,_) in CASES.items():
            with self.subTest(name):
                self.assertEqual(len(matches(good)),1,good)

    def test_near_misses_do_not_match(self):
        for name,(_,bad) in CASES.items():
            for message in bad:
                with self.subTest(name=name,message=message):
                    self.assertEqual(matches(message),[],message)

    def test_unrelated_failures_do_not_match(self):
        for message in ("real failure","Out of memory: Killed process 1234 (firefox)","nvme nvme0: I/O 12 QID 3 timeout, aborting","Failed to start Network Manager."):
            self.assertEqual(matches(message),[],message)

    def test_every_reason_is_a_nonempty_explanation(self):
        for pattern,why in doctor.BENIGN_JOURNAL:
            self.assertTrue(why.strip(),pattern)

class BenignJournalStaysVisible(unittest.TestCase):
    def test_near_misses_still_count_through_the_journal_check(self):
        for name,(_,bad) in CASES.items():
            for message in bad:
                with self.subTest(name=name,message=message):
                    row=journal(("svc",message))
                    self.assertEqual((row['state'],row['metrics']['journal_entries'],row['metrics']['journal_ignored']),('warn',1,0))
                    self.assertNotIn('[ignored:',row['evidence'])

    def test_matched_notice_is_ignored_with_reason_and_still_reported(self):
        for name,(good,_) in CASES.items():
            with self.subTest(name):
                row=journal(("kernel",good))
                self.assertEqual(row['state'],'ok')
                self.assertEqual((row['metrics']['journal_entries'],row['metrics']['journal_ignored']),(0,1))
                self.assertIn(good,row['evidence'])
                self.assertIn('kernel: '+good,row['evidence'])
                self.assertIn('[ignored: '+matches(good)[0]+']',row['evidence'])

    def test_matched_notice_never_hides_a_real_failure_next_to_it(self):
        good=CASES["TDX"][0]
        row=journal(("kernel",good),("app","real failure"),("kernel",CASES["ucsi GET_CURRENT_CAM"][0]))
        self.assertEqual((row['state'],row['metrics']['journal_entries'],row['metrics']['journal_ignored']),('warn',1,2))
        evidence=row['evidence']
        self.assertIn('app: real failure',evidence)
        self.assertEqual(evidence.count('[ignored:'),2)
        # Real findings are listed before the ignored ones, so the ignored notices never lead the evidence.
        self.assertLess(evidence.index('app: real failure'),evidence.index('[ignored:'))

    def test_ignored_entry_falls_back_to_comm_when_identifier_is_missing(self):
        line=json.dumps({"_COMM":"wpa_supplicant","MESSAGE":CASES["nl80211 multicast"][0]})
        row=doctor.Probes(lambda *a,**kw:probe(line)).journal()
        self.assertEqual(row['metrics']['journal_ignored'],1)
        self.assertIn('wpa_supplicant: '+CASES["nl80211 multicast"][0]+'  [ignored:',row['evidence'])

if __name__=='__main__':unittest.main()
