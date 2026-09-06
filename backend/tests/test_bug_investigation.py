import sys
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.agents.investigation import (
    BugInvestigationReport,
    bug_investigation_graph,
)
from app.agents.investigation.steps import (
    MAX_INVESTIGATION_STEPS,
    evaluate_hypotheses,
    gather_evidence,
    generate_hypotheses,
    identify_entry_points,
    trace_code,
    understand_bug,
)


class TestBugInvestigation(unittest.TestCase):
    """Unit and integration tests for Phase 3 Part 1 Bug Investigation."""

    def test_01_bug_normalization(self):
        """Test 1 — Bug normalization: extracts structured problem without inventing facts."""
        # Vague input
        vague_state = understand_bug({"bug_report": "Login is broken."})
        vague_norm = vague_state["normalized_problem"]
        self.assertEqual(vague_norm["component"], "authentication")
        self.assertTrue(len(vague_norm["known_facts"]) > 0)
        self.assertTrue(len(vague_norm["assumptions"]) > 0)
        self.assertIn("Login is broken.", vague_norm["known_facts"][0])

        # Specific input with HTTP method and status code
        spec_state = understand_bug({"bug_report": "POST /api/login gives 500 when user refreshes"})
        spec_norm = spec_state["normalized_problem"]
        self.assertEqual(spec_norm["component"], "authentication")
        self.assertEqual(spec_norm["endpoint_or_operation"], "POST /API/LOGIN")
        self.assertEqual(spec_norm["error_type"], "HTTP 500")

    def test_02_identify_entry_points(self):
        """Test 2 — Entry point discovery: finds relevant route handlers using CodeGraph."""
        state = understand_bug({"bug_report": "Repository analysis fails during ingestion"})
        state = identify_entry_points(state)

        entry_point_names = [ep["name"] for ep in state["entry_points"]]
        self.assertIn("analyze_repository", entry_point_names)
        self.assertTrue(len(state["relevant_files"]) > 0)

    def test_03_call_tracing(self):
        """Test 3 — Call tracing: follows execution chain starting from entry points."""
        state = understand_bug({"bug_report": "analyze repository returns error"})
        state = identify_entry_points(state)
        state = trace_code(state)

        all_child_calls = []
        for trace in state["call_traces"]:
            all_child_calls.extend([c["name"] for c in trace.get("calls", [])])
        self.assertTrue(
            any(name in all_child_calls for name in ("get_repository", "parse_python_file", "chunk_code")),
            f"Expected known calls in {all_child_calls}",
        )

    def test_04_hypothesis_generation_and_evaluation(self):
        """Test 4 — Hypotheses: generates multiple competing hypotheses with supporting evidence."""
        state = understand_bug({"bug_report": "POST /analyze gives 500 error"})
        state = identify_entry_points(state)
        state = gather_evidence(state)
        state = trace_code(state)
        state = generate_hypotheses(state)

        hypotheses = state["hypotheses"]
        self.assertGreaterEqual(len(hypotheses), 2)

        # Verify hypothesis structure
        for h in hypotheses:
            self.assertIn("id", h)
            self.assertIn("title", h)
            self.assertIn("supporting_evidence", h)
            self.assertIn("contradicting_evidence", h)
            self.assertIn("confidence", h)
            self.assertIsInstance(h["confidence"], float)

        state = evaluate_hypotheses(state)
        self.assertIsNotNone(state.get("selected_hypothesis"))
        self.assertIn(state.get("confidence"), ("High", "Medium", "Low"))

    def test_05_evidence_tracking_and_citations(self):
        """Test 5 — Evidence tracking: every evidence item contains valid file and line location."""
        state = understand_bug({"bug_report": "chat endpoint fails"})
        state = identify_entry_points(state)
        state = gather_evidence(state)

        evidence = state["evidence"]
        self.assertTrue(len(evidence) > 0)
        for ev in evidence:
            self.assertIn("file_path", ev)
            self.assertIn("line_number", ev)
            self.assertIn("type", ev)
            self.assertIn("description", ev)
            self.assertTrue(len(ev["file_path"]) > 0)

    def test_06_bounded_investigation(self):
        """Test 6 — Bounded investigation: loops strictly stop at MAX_INVESTIGATION_STEPS."""
        state = {
            "bug_report": "Infinite loop test",
            "step_count": MAX_INVESTIGATION_STEPS,
            "hypotheses": [{"id": "H1", "confidence": 0.2}],
        }
        res = evaluate_hypotheses(state)
        self.assertTrue(res["is_conclusive"])

    def test_07_full_workflow_real_codescout_analysis(self):
        """Integration Test 1: Where could repository analysis fail?"""
        initial_state = {
            "bug_report": "Where could repository analysis fail when ingesting a GitHub repo?",
            "repository": "backend",
        }
        result = bug_investigation_graph.invoke(initial_state)

        report = result.get("final_report", {})
        self.assertIn("summary", report)
        self.assertIn("likely_root_cause", report)
        self.assertIn("entry_points", report)
        self.assertIn("call_chain", report)
        self.assertIn("hypotheses", report)
        self.assertIn("recommended_next_step", report)

        # Entry points should include analyze_repository
        self.assertIn("analyze_repository", report["entry_points"])
        # Should have concrete call chains
        self.assertTrue(len(report["call_chain"]) > 0)
        # Recommended next step should advise running tests
        self.assertIn("test", report["recommended_next_step"].lower())

    def test_08_full_workflow_chat_flow(self):
        """Integration Test 2: What happens when a user sends a chat question?"""
        initial_state = {
            "bug_report": "What happens when a user sends a chat question?",
            "repository": "backend",
        }
        result = bug_investigation_graph.invoke(initial_state)

        report = result.get("final_report", {})
        self.assertIn("chat", report["entry_points"])
        self.assertTrue(any("chat.py" in f for f in report["relevant_files"]))


if __name__ == "__main__":
    unittest.main()
