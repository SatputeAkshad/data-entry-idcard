import unittest
from backend.app.domain import State,transition,validate_fields,validate_student,validate_mapping,sheet_positions
class DomainTests(unittest.TestCase):
    def setUp(self): self.fields=[{'key':'full_name','label':'Name','required':True},{'key':'class','label':'Class','type':'select','options':['1','2']}]
    def test_form_config(self):
        validate_fields(self.fields)
        with self.assertRaises(ValueError): validate_fields(self.fields+[self.fields[0]])
    def test_required_and_dropdown(self):
        for data in ({'full_name':''},{'full_name':'A','class':'3'},{'full_name':'A','unknown':'X'},{'full_name':None}):
            with self.assertRaises(ValueError): validate_student(self.fields,data)
        validate_student(self.fields,{},draft=True)
    def test_capture_approval_and_unlimited_retake(self):
        state=State.READY
        for _ in range(100):
            for target in (State.REQUESTED,State.WAITING,State.RECEIVED,State.REVIEWING,State.RETAKE): state=transition(state,target)
        for target in (State.REQUESTED,State.WAITING,State.RECEIVED,State.REVIEWING,State.APPROVED): state=transition(state,target)
        with self.assertRaises(ValueError): transition(state,State.RECEIVED)
    def test_rejected_cannot_approve(self):
        with self.assertRaises(ValueError): transition(State.RETAKE,State.APPROVED)
    def test_waiting_cannot_approve(self):
        with self.assertRaises(ValueError): transition(State.WAITING,State.APPROVED)
    def test_mapping(self):
        validate_mapping({'NAME':'full_name','PHOTO':'photo'},['full_name'])
        for m in ({'NAME':'unknown','PHOTO':'photo'},{'NAME':'full_name'},{'':'photo'}):
            with self.assertRaises(ValueError): validate_mapping(m,['full_name'])
    def test_physical_sheet(self):
        p=sheet_positions(210,297,85.6,54,10,5)
        self.assertEqual(len(p),8)
        self.assertEqual(p[1],(100.6,10))
    def test_bleed_and_invalid_sheet(self):
        p=sheet_positions(210,297,85.6,54,10,5,3)
        self.assertEqual(p[0],(13,13))
        for args in ((10,10,85,54,10,5),(210,297,85,54,-1,5),(float('nan'),297,85,54,10,5)):
            with self.assertRaises(ValueError): sheet_positions(*args)
if __name__=='__main__': unittest.main()
