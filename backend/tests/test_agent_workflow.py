import sys
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.agents.graph import (
    MAX_TOOL_CALLS,
    choose_tool,
    code_scout_graph,
    evaluate_evidence,
    understand_question,
)


class TestAgentWorkflow(unittest.TestCase):
    """Integration and workflow tests for the LangGraph codebase investigation agent."""

    def test_01_tool_selection_heuristics(self):
        """Verify that questions map to the appropriate investigation tool."""
        # 1. Callers query
        st1 = understand_question({"question": "Who calls validate_token?", "repository": "test/repo"})
        st1 = choose_tool(st1)
        self.assertEqual(st1["next_tool"]["tool"], "find_callers")
        self.assertEqual(st1["next_tool"]["args"]["symbol"], "validate_token")

        # 2. Callees query
        st2 = understand_question({"question": "What does AuthService.login call?", "repository": "test/repo"})
        st2 = choose_tool(st2)
        self.assertEqual(st2["next_tool"]["tool"], "find_callees")
        self.assertEqual(st2["next_tool"]["args"]["symbol"], "AuthService.login")

        # 3. Definition query
        st3 = understand_question({"question": "Where is 'chat' defined?", "repository": "test/repo"})
        st3 = choose_tool(st3)
        self.assertEqual(st3["next_tool"]["tool"], "find_definition")
        self.assertEqual(st3["next_tool"]["args"]["symbol"], "chat")

        # 4. Dependents query
        st4 = understand_question({"question": "What files depend on app/routes/chat.py?", "repository": "test/repo"})
        st4 = choose_tool(st4)
        self.assertEqual(st4["next_tool"]["tool"], "get_dependents")

        # 5. Semantic search query
        st5 = understand_question({"question": "How is authentication handled?", "repository": "test/repo"})
        st5 = choose_tool(st5)
        self.assertEqual(st5["next_tool"]["tool"], "search_code")

    def test_02_bounded_tool_execution(self):
        """Verify that tool execution terminates strictly within MAX_TOOL_CALLS without looping."""
        state = {
            "question": "Continuous loop test question",
            "repository": "test/repo",
            "investigation_step": MAX_TOOL_CALLS,
            "tool_calls": [],
        }
        res = choose_tool(state)
        self.assertTrue(res.get("is_sufficient"))
        self.assertIsNone(res.get("next_tool"))

    def test_03_real_codescout_investigation_chat_endpoint(self):
        """Integration Test 1: Where is the chat endpoint implemented?"""
        initial_state = {
            "question": "Where is the chat endpoint implemented?",
            "repository": "backend",
        }
        result = code_scout_graph.invoke(initial_state)

        self.assertIn("answer", result)
        self.assertTrue(len(result["answer"]) > 0)
        # Should have executed investigation tools
        self.assertTrue(len(result.get("tool_calls", [])) > 0)
        # Should have discovered app/routes/chat.py
        evidence_blob = " ".join(result.get("evidence", [])) + result.get("answer", "")
        self.assertIn("chat", evidence_blob.lower())

    def test_04_real_codescout_investigation_callers(self):
        """Integration Test 2: Who calls should_analyze_file?"""
        initial_state = {
            "question": "Who calls should_analyze_file?",
            "repository": "backend",
        }
        result = code_scout_graph.invoke(initial_state)

        evidence_blob = " ".join(result.get("evidence", [])) + result.get("answer", "")
        # should_analyze_file is called by analyze_repository
        self.assertIn("analyze_repository", evidence_blob)

    def test_05_anti_hallucination_on_missing_symbol(self):
        """Verify that an unknown symbol is reported honestly rather than hallucinating."""
        initial_state = {
            "question": "Where is FakeNonExistentMethod_XYZ defined?",
            "repository": "backend",
        }
        result = code_scout_graph.invoke(initial_state)

        evidence_blob = " ".join(result.get("evidence", [])) + result.get("answer", "")
        self.assertTrue(
            "not found" in evidence_blob.lower() or "could not" in evidence_blob.lower(),
            "Agent should report that FakeNonExistentMethod_XYZ was not found",
        )


if __name__ == "__main__":
    unittest.main()
