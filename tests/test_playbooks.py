import unittest
from devcity.guide.playbooks import load_playbook, list_playbooks


class TestPlaybooks(unittest.TestCase):
    def test_list_playbooks(self):
        pbs = list_playbooks()
        self.assertIn("react-springboot-postgres", pbs)

    def test_load_full_stack_playbook(self):
        pb = load_playbook("react-springboot-postgres")
        self.assertIsNotNone(pb)
        self.assertGreaterEqual(len(pb.steps), 8)
        self.assertIn("React", pb.title)

        step1 = pb.steps[0]
        self.assertEqual(step1.step_number, 1)
        self.assertTrue(step1.prompt_template)
        self.assertTrue(len(step1.checklist) > 0)


if __name__ == "__main__":
    unittest.main()
