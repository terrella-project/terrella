"""Tests for the graders and guards in stack/scripts/eval-local-models.py.

Run: uv run --with pytest pytest stack/scripts/tests
The sandbox and ollama are faked; nothing here needs a GPU, podman or a model.
"""

import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("evalm", HERE.parent / "eval-local-models.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)


def runner(ok):
    calls = []

    def run(code):
        calls.append(code)
        return {"ok": ok(code) if callable(ok) else ok, "exit": 0, "stdout": "", "stderr": ""}

    run.calls = calls
    return run


FIM = {"id": "t", "prefix": "def f(x):\n", "suffix": "\nprint(f(2))\n",
       "expected": "    return x * 2\n", "test": "assert f(2) == 4"}


# -- FIM ---------------------------------------------------------------------

class TestFim:
    def test_exact(self):
        assert ev.grade_fim(FIM, "    return x * 2\n", "stop")[0] == ev.PASS

    def test_whitespace_inside_line_is_ignored(self):
        assert ev.grade_fim(FIM, "  return   x * 2", "stop")[0] == ev.PASS

    def test_wrong(self):
        assert ev.grade_fim(FIM, "    return x + 2\n", "stop")[0] == ev.FAIL

    def test_lines_after_the_hole_are_cut(self):
        st, d = ev.grade_fim(FIM, "    return x * 2\n\nprint(f(2))\nprint(1)\n", "length")
        assert st == ev.PASS and d["line_match"]

    def test_empty(self):
        assert ev.grade_fim(FIM, "  \n", "stop")[0] == ev.EMPTY

    def test_truncated_only_when_short_and_cut_off(self):
        two = dict(FIM, expected="    y = x\n    return y * 2\n")
        assert ev.grade_fim(two, "    y = x\n", "length")[0] == ev.TRUNCATED
        assert ev.grade_fim(two, "    y = x\n", "stop")[0] == ev.FAIL

    def test_exec_passes_an_equivalent_completion(self):
        run = runner(True)
        st, d = ev.grade_fim(FIM, "    return 2 * x\n", "stop", run)
        assert st == ev.PASS and d == {"line_match": False, "exec_pass": True}
        assert run.calls[0].startswith(FIM["prefix"] + "    return 2 * x\n" + FIM["suffix"])
        assert run.calls[0].rstrip().endswith(FIM["test"])

    def test_exec_tries_the_full_completion_when_the_cut_fails(self):
        run = runner(lambda code: "return x * 2 + z" in code)
        st, _ = ev.grade_fim(FIM, "    z = 1\n    return x * 2 + z - 1\n", "stop", run)
        assert st == ev.PASS
        assert len(run.calls) == 2

    def test_exec_and_line_both_fail(self):
        st, d = ev.grade_fim(FIM, "    return 0\n", "stop", runner(False))
        assert st == ev.FAIL and d["exec_pass"] is False

    def test_no_test_means_line_match_only(self):
        t = dict(FIM, test=None)
        run = runner(True)
        assert ev.grade_fim(t, "    return 2 * x\n", "stop", run)[0] == ev.FAIL
        assert run.calls == []


# -- reasoning ---------------------------------------------------------------

class TestReason:
    @pytest.mark.parametrize("content,want", [
        ("ANSWER: 1\u202f234", "1234"),
        ("so...\nANSWER: 42", "42"),
        ("**ANSWER:** 1,234", "1,234"),
        ("Answer = 7", "7"),
        ("Final answer: 12", "12"),
        ("**Final Answer:** Tuesday", "Tuesday"),
        ("ANSWER: 3\nwait, no\nANSWER: 4", "4"),
        ("the answer is 5", None),
        ("", None),
    ])
    def test_parse_answer(self, content, want):
        assert ev.parse_answer(content) == want

    @pytest.mark.parametrize("task,value,ok", [
        ({"answer": "1234", "answer_type": "int"}, "1,234", True),
        ({"answer": "1234", "answer_type": "int"}, "$1234", True),
        ({"answer": "1234", "answer_type": "int"}, "1235", False),
        ({"answer": "1234", "answer_type": "int"}, "about twelve hundred", False),
        ({"answer": "3.1416", "answer_type": "decimal"}, "3.14159", True),
        ({"answer": "3.1416", "answer_type": "decimal"}, "3.15", False),
        ({"answer": "-12", "answer_type": "int"}, "−12", True),
        ({"answer": "14:30", "answer_type": "text"}, "14:30.", True),
        ({"answer": "Tuesday", "answer_type": "text"}, "tuesday", True),
        ({"answer": "Tuesday", "answer_type": "text"}, "Thursday", False),
        ({"answer": ["NYC", "New York"], "answer_type": "text"}, "new york", True),
    ])
    def test_answer_correct(self, task, value, ok):
        assert ev.answer_correct(task, value) is ok

    def test_statuses(self):
        t = {"answer": "9", "answer_type": "int"}
        assert ev.grade_reason(t, "ANSWER: 9", "stop")[0] == ev.PASS
        assert ev.grade_reason(t, "ANSWER: 8", "stop")[0] == ev.FAIL
        assert ev.grade_reason(t, "thinking and thinking", "length")[0] == ev.TRUNCATED
        assert ev.grade_reason(t, "it is nine", "stop")[0] == ev.UNPARSABLE
        assert ev.grade_reason(t, "", "stop")[0] == ev.EMPTY


# -- generalist ----------------------------------------------------------------

GEN = {"required": [["prometheus"], [r"\b137\b", "killed"]], "forbidden": [r"grafana.{0,20}down"]}


class TestGeneral:
    def test_pass(self):
        st, d = ev.grade_general(GEN, "Prometheus was killed.", "stop")
        assert st == ev.PASS and d["facts"] == "2/2"

    def test_missing_fact(self):
        st, d = ev.grade_general(GEN, "Prometheus stopped.", "stop")
        assert st == ev.FAIL and d["missing"] == [r"\b137\b"]

    def test_invented_fact_fails_even_with_all_facts(self):
        st, d = ev.grade_general(GEN, "Prometheus exited 137; grafana is down.", "stop")
        assert st == ev.FAIL and d["invented"]

    def test_digit_group_spaces(self):
        t = {"required": [[r"14\.79"], [r"\b1234\b"]], "forbidden": []}
        assert ev.grade_general(t, "$14.79 total; 1\u202f234 calls", "stop")[0] == ev.PASS

    def test_empty_and_truncated(self):
        assert ev.grade_general(GEN, "", "stop")[0] == ev.EMPTY
        assert ev.grade_general(GEN, "Prometheus 137", "length")[0] == ev.TRUNCATED
        assert ev.grade_general(GEN, "", "length")[0] == ev.TRUNCATED

    def test_shipped_tasks_references_pass_and_a_blank_answer_fails(self):
        for t in ev.load_tasks("general"):
            assert ev.grade_general(t, t["reference"], "stop")[0] == ev.PASS, t["id"]
            assert ev.grade_general(t, "I cannot tell from this.", "stop")[0] == ev.FAIL, t["id"]


# -- code ----------------------------------------------------------------------

class TestCode:
    def test_extract_longest_block(self):
        c = "```python\nx=1\n```\ntext\n```py\ndef f():\n    return 1\n```"
        assert ev.extract_code(c).startswith("def f")

    def test_extract_bare_def(self):
        assert ev.extract_code("def f():\n    return 1\n").startswith("def f")

    def test_extract_none(self):
        assert ev.extract_code("I would use a loop.") is None

    def test_grade(self):
        t = {"tests": "assert f() == 1"}
        good = "```python\ndef f():\n    return 1\n```"
        run = runner(True)
        assert ev.grade_code(t, good, "stop", run)[0] == ev.PASS
        assert run.calls[0].rstrip().endswith("assert f() == 1")
        assert ev.grade_code(t, good, "stop", runner(False))[0] == ev.FAIL
        assert ev.grade_code(t, "no code here", "stop", run)[0] == ev.UNPARSABLE
        assert ev.grade_code(t, "Let me think about", "length", run)[0] == ev.TRUNCATED
        assert ev.grade_code(t, "", "stop", run)[0] == ev.EMPTY
        # all budget spent thinking: no content, cut off
        assert ev.grade_code(t, "", "length", run)[0] == ev.TRUNCATED


# -- embeddings ------------------------------------------------------------------

class TestEmbed:
    def test_chunks_split_at_h1_h2_not_inside_fences(self):
        md = "# Title\nintro\n\n## A\ntext a\n```\n## not a heading\n```\n### sub\nmore\n## `B` [x](y)\nb\n"
        ids = [c["id"] for c in ev.chunk_markdown("d.md", md)]
        assert ids == ["d.md#Title", "d.md#A", "d.md#B x"]

    def test_long_section_split_keeps_its_section(self):
        md = "## Big\n" + "\n\n".join(["word " * 50] * 10)
        chunks = ev.chunk_markdown("d.md", md, limit=600)
        assert len(chunks) > 1
        assert all(c["section"] == "d.md#Big" for c in chunks)
        assert chunks[0]["id"] == "d.md#Big [1]"
        assert all(len(c["text"]) <= 600 for c in chunks)

    def test_rank_sections_takes_the_best_chunk_per_section(self):
        chunks = [{"section": "a"}, {"section": "a"}, {"section": "b"}]
        vecs = [[0, 1], [1, 0], [0.7, 0.7]]
        assert ev.rank_sections([1, 0], chunks, vecs) == ["a", "b"]

    def test_metrics(self):
        m = ev.retrieval_metrics([["x", "y"], ["y", "x"], ["z"]],
                                 [["x"], ["x"], ["x"]])
        assert m["recall@1"] == pytest.approx(1 / 3)
        assert m["recall@5"] == pytest.approx(2 / 3)
        assert m["mrr"] == pytest.approx((1 + 0.5) / 3)


# -- guards ------------------------------------------------------------------------

class FakeClient:
    def __init__(self, loaded):
        self.loaded = loaded

    def ps(self):
        return self.loaded


class TestGuards:
    def test_residency_spilled_and_shared(self):
        c = FakeClient([{"name": "m:latest", "size": 10, "size_vram": 9},
                        {"name": "other:1b", "size": 1, "size_vram": 1}])
        r = ev.residency(c, "m")
        assert r["spilled"] and r["others"] == ["other:1b"]

    def test_residency_whole(self):
        r = ev.residency(FakeClient([{"name": "m:7b", "size": 5, "size_vram": 5}]), "m:7b")
        assert r["loaded"] and not r["spilled"] and not r["others"]

    def test_residency_not_loaded(self):
        assert ev.residency(FakeClient([]), "m")["loaded"] is False

    def test_sleep_mid_sample_is_an_error(self):
        rec = ev.sample_record("t", ev.PASS, {}, {}, "out", slept=120)
        assert rec["status"] == ev.ERROR and "slept" in rec["error"]
        assert ev.sample_record("t", ev.PASS, {}, {}, "out", slept=0.2)["status"] == ev.PASS

    def test_summarize_speed_comes_from_ollama_counters(self):
        s = [{"status": ev.PASS, "eval_count": 100, "eval_ns": 1e9, "total_ns": 2e9,
              "load_ns": 1e9},
             {"status": ev.FAIL, "eval_count": 300, "eval_ns": 1e9, "total_ns": 3e9}]
        out = ev.summarize(s, 3)
        assert out["tok_s_p50"] == 200 and out["tok_s_min"] == 100
        assert out["latency_ms_p50"] == 1000
        assert out["n_done"] == 2 and out["pass"] == 1

    def test_speed_ignores_replies_too_short_to_have_a_rate(self):
        s = [{"status": ev.PASS, "eval_count": 1, "eval_ns": 1000},
             {"status": ev.PASS, "eval_count": 50, "eval_ns": 5e8}]
        out = ev.summarize(s, 2)
        assert out["tok_s_p50"] == 100 and out["tok_s_max"] == 100 and out["tok_s_n"] == 1

    def test_finish_flags_incomplete_and_warnings(self, tmp_path):
        run = ev.Run.__new__(ev.Run)
        run.cells, run.meta, run.out = [], {}, tmp_path / "r.json"
        cell = {"role": "reason", "model": "m", "flags": []}
        run.finish(cell, [{"task": "a", "status": ev.PASS},
                          {"task": "b", "status": ev.TRUNCATED}], 3)
        assert "INCOMPLETE" in cell["flags"] and "TRUNCATEDx1" in cell["flags"]
        assert json.loads(run.out.read_text())["cells"][0]["model"] == "m"

    def test_score_denominator_is_the_task_count(self, capsys):
        cell = {"role": "code", "model": "m", "flags": ["TRUNCATEDx4"],
                "summary": {"pass": 16, "graded": 16, "n_expected": 20}}
        ev.print_report([cell])
        assert "16/20" in capsys.readouterr().out

    def test_sampling_options(self):
        run = ev.Run.__new__(ev.Run)
        run.seed = 29
        run.sampling = "greedy"
        assert run.opts("reason")["temperature"] == 0
        run.sampling = "model"
        o = run.opts("reason")
        assert "temperature" not in o and o["seed"] == 29 and o["num_predict"] == 12288

    def test_thinking_tail_is_kept(self):
        rec = ev.sample_record("t", ev.TRUNCATED, {}, {}, "", thinking="x" * 5000 + "END")
        assert rec["thinking_chars"] == 5003 and rec["thinking_tail"].endswith("END")
        assert len(rec["thinking_tail"]) == 1500

    def test_wait_for_memory_waits_then_goes(self):
        readings = iter([4.0, 8.0, 20.0])
        slept = []
        ok, free = ev.wait_for_memory(12, reader=lambda: next(readings), sleep=slept.append,
                                      poll_s=30)
        assert ok and free == 20.0 and slept == [30, 30]

    def test_wait_for_memory_gives_up(self):
        slept = []
        ok, free = ev.wait_for_memory(12, max_wait_s=60, poll_s=30, reader=lambda: 3.0,
                                      sleep=slept.append)
        assert not ok and free == 3.0 and slept == [30, 30]

    def test_wait_for_memory_without_meminfo_goes(self):
        assert ev.wait_for_memory(12, reader=lambda: None, sleep=lambda s: None) == (True, None)

    def test_think_param(self):
        run = ev.Run.__new__(ev.Run)
        for mode, want in [("default", {}), ("off", {"think": False}), ("low", {"think": "low"})]:
            run.think = mode
            assert run.think_param() == want

    @pytest.mark.parametrize("flags,code", [([], 0), (["SPILLED"], 2), (["INCOMPLETE"], 1),
                                            (["NOT-INSTALLED"], 1), (["LOW-MEMORY"], 1)])
    def test_report_exit_code(self, flags, code, capsys):
        cell = {"role": "reason", "model": "m", "flags": flags,
                "summary": {"pass": 1, "graded": 1, "n_expected": 1}}
        assert ev.print_report([cell]) == code


def test_validate_tasks_catches_duplicates_and_missing_fields():
    probs = ev.validate_tasks("code", [{"id": "a", "prompt": "", "entry": "f", "tests": "",
                                        "reference": ""}, {"id": "a"}])
    assert any("duplicate" in p for p in probs)
    assert any("missing" in p for p in probs)
    assert ev.validate_tasks("code", []) == ["code: no tasks"]


# -- agent tool loop -----------------------------------------------------------------

AGENT = {"expect_tool": "Glob", "expect_args": r"\.container", "expect_final": r"litellm"}


def use(name, args=None):
    return {"type": "tool_use", "id": "t1", "name": name, "input": args or {}}


def text(t, stop="end_turn"):
    return {"content": [{"type": "text", "text": t}], "stop_reason": stop}


def calls(*blocks):
    return {"content": list(blocks), "stop_reason": "tool_use"}


AGENT_T = {**AGENT, "tool_result": "a.container\nterrella-litellm.container",
           "fallback": {"Read": "file text"}}


class TestAgent:

    def test_right_tool_then_answer(self):
        st = {}
        status, results = ev.agent_step(AGENT_T, calls(use("Glob", {"pattern": "*.container"})), st)
        assert status is None and results[0]["content"].startswith("a.container")
        assert results[0]["tool_use_id"] == "t1"
        assert ev.agent_step(AGENT_T, text("terrella-litellm.container"), st)[0] == ev.PASS
        assert st["calls"] == ["Glob"] and st["extra"] == 0

    def test_fallback_tool_first_is_allowed_and_counted(self):
        st = {}
        assert ev.agent_step(AGENT_T, calls(use("Read", {"path": "x"})), st)[0] is None
        assert ev.agent_step(AGENT_T, calls(use("Glob", {"pattern": "*.container"})), st)[0] is None
        assert ev.agent_step(AGENT_T, text("litellm"), st)[0] == ev.PASS
        assert st["extra"] == 1 and st["calls"] == ["Read", "Glob"]

    def test_answer_from_fallback_alone_fails(self):
        st = {}
        ev.agent_step(AGENT_T, calls(use("Read", {"path": "x"})), st)
        assert ev.agent_step(AGENT_T, text("litellm"), st)[0] == ev.FAIL
        assert st["step"] == "answered without using the tool"

    def test_tool_that_cannot_help(self):
        st = {}
        assert ev.agent_step(AGENT_T, calls(use("Grep", {"pattern": "x"})), st)[0] == ev.FAIL
        assert "cannot help" in st["step"]

    def test_wrong_args(self):
        st = {}
        assert ev.agent_step(AGENT_T, calls(use("Glob", {"pattern": "*.py"})), st)[0] == ev.FAIL
        assert st["step"] == "wrong arguments"

    def test_every_call_in_a_parallel_reply_gets_a_result(self):
        b2 = {**use("Read", {"path": "x"}), "id": "t2"}
        _, results = ev.agent_step(AGENT_T, calls(use("Glob", {"pattern": "a.container"}), b2), {})
        assert [r["tool_use_id"] for r in results] == ["t1", "t2"]

    def test_wrong_final_empty_and_cut_off(self):
        st = {"hit": True}
        assert ev.agent_step(AGENT_T, text("none"), dict(st))[0] == ev.FAIL
        assert ev.agent_step(AGENT_T, text(""), dict(st))[0] == ev.EMPTY
        assert ev.agent_step(AGENT_T, text("", "max_tokens"), dict(st))[0] == ev.TRUNCATED

    def test_no_tool_task(self):
        t = {"expect_tool": None, "expect_final": r"\b391\b"}
        assert ev.agent_step(t, text("391"), {})[0] == ev.PASS
        assert ev.agent_step(t, text("392"), {})[0] == ev.FAIL
        assert ev.agent_step(t, calls(use("Glob")), {})[0] == ev.FAIL

    def test_digit_group_spaces(self):
        t = {"expect_tool": None, "expect_final": r"\b5,?069\b"}
        assert ev.agent_step(t, text("**5\u202f069 MiB**"), {})[0] == ev.PASS
        assert ev.agent_step(t, text("5\u00a0069"), {})[0] == ev.PASS
        assert ev.agent_step(t, text("5 069"), {})[0] == ev.FAIL  # a plain space is not a separator

    def test_shipped_tasks_reference_answers_match(self):
        for t in ev.load_tasks("agent"):
            assert ev.re.search(t["expect_final"], t["reference_final"], ev.re.IGNORECASE), t["id"]
