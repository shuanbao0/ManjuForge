"""Unit tests for the async-task primitives in ``ComicGenPipeline``.

These three helpers (``_register_task`` / ``_task_lifecycle`` /
``_run_per_item_batch`` / ``_run_one_shot``) are the foundation for
every background job in the app, so we lock down their contract here.
"""
import pytest

from src.apps.comic_gen.pipeline import ComicGenPipeline


def _bare_pipeline():
    p = ComicGenPipeline.__new__(ComicGenPipeline)
    p.asset_generation_tasks = {}
    p.video_generation_tasks = {}
    p._save_data = lambda: None
    return p


# === _register_task =======================================================


def test_register_task_envelope_has_all_batch_fields():
    """Every consumer reads completed_count / failed_count / errors /
    current_item_id without checking presence — they must always exist."""
    p = _bare_pipeline()
    tid = p._register_task(task_type="x", script_id="s1")
    task = p.asset_generation_tasks[tid]
    for k in ("status", "progress", "error", "task_type", "script_id",
              "created_at", "completed_count", "failed_count", "errors",
              "current_item_id"):
        assert k in task, f"missing {k}"
    assert task["status"] == "pending"
    assert task["progress"] == 0
    assert task["completed_count"] == 0
    assert task["failed_count"] == 0
    assert task["errors"] == {}


def test_register_task_extra_fields_passthrough():
    p = _bare_pipeline()
    tid = p._register_task(task_type="x", script_id="s1", asset_id="a1", asset_type="character")
    task = p.asset_generation_tasks[tid]
    assert task["asset_id"] == "a1"
    assert task["asset_type"] == "character"


def test_register_task_video_store_routes_to_video_dict():
    p = _bare_pipeline()
    tid = p._register_task(task_type="motion", script_id="s1", store="video")
    assert tid in p.video_generation_tasks
    assert tid not in p.asset_generation_tasks


# === _task_lifecycle ======================================================


def test_lifecycle_marks_completed_on_normal_exit():
    p = _bare_pipeline()
    tid = p._register_task(task_type="x", script_id="s1")
    with p._task_lifecycle(tid) as task:
        assert task["status"] == "processing"
    assert p.asset_generation_tasks[tid]["status"] == "completed"
    assert p.asset_generation_tasks[tid]["progress"] == 100


def test_lifecycle_records_exception_as_failed():
    p = _bare_pipeline()
    tid = p._register_task(task_type="x", script_id="s1")
    with p._task_lifecycle(tid) as _:
        raise RuntimeError("boom")  # noqa: TRY301
    task = p.asset_generation_tasks[tid]
    assert task["status"] == "failed"
    assert task["error"] == "boom"


def test_lifecycle_respects_worker_set_status():
    """If the worker explicitly set status (e.g. partial-failure batch),
    the lifecycle must not clobber it back to 'completed'."""
    p = _bare_pipeline()
    tid = p._register_task(task_type="x", script_id="s1")
    with p._task_lifecycle(tid) as task:
        task["status"] = "completed"  # simulate manual finalize
        task["progress"] = 100
    assert p.asset_generation_tasks[tid]["status"] == "completed"


def test_lifecycle_missing_task_no_crash():
    """If a worker is invoked for a task that vanished, log + return —
    not a crash that kills the BackgroundTasks loop."""
    p = _bare_pipeline()
    with p._task_lifecycle("nonexistent") as _:
        pass  # should silently no-op


# === _run_per_item_batch ==================================================


class _Item:
    def __init__(self, id_):
        self.id = id_


def test_batch_runs_work_for_each_item():
    p = _bare_pipeline()
    tid = p._register_task(task_type="batch", script_id="s1")
    seen = []
    p._run_per_item_batch(tid, [_Item("a"), _Item("b"), _Item("c")], lambda x: seen.append(x.id))
    assert seen == ["a", "b", "c"]
    assert p.asset_generation_tasks[tid]["completed_count"] == 3
    assert p.asset_generation_tasks[tid]["failed_count"] == 0
    assert p.asset_generation_tasks[tid]["progress"] == 100


def test_batch_isolates_item_failures():
    p = _bare_pipeline()
    tid = p._register_task(task_type="batch", script_id="s1")

    def work(item):
        if item.id == "b":
            raise ValueError("nope")

    p._run_per_item_batch(tid, [_Item("a"), _Item("b"), _Item("c")], work)
    task = p.asset_generation_tasks[tid]
    assert task["completed_count"] == 2
    assert task["failed_count"] == 1
    assert task["errors"] == {"b": "nope"}


def test_batch_empty_items_no_op():
    p = _bare_pipeline()
    tid = p._register_task(task_type="batch", script_id="s1")
    p._run_per_item_batch(tid, [], lambda x: pytest.fail("should not run"))
    assert p.asset_generation_tasks[tid]["progress"] == 0


def test_batch_clears_current_item_id_on_finish():
    p = _bare_pipeline()
    tid = p._register_task(task_type="batch", script_id="s1")
    p._run_per_item_batch(tid, [_Item("only")], lambda x: None)
    assert p.asset_generation_tasks[tid]["current_item_id"] is None


def test_batch_save_data_failure_does_not_abort_loop():
    """A botched _save_data on one frame must not stop the rest of the
    batch — losing one frame's persistence is better than failing 50."""
    p = _bare_pipeline()
    call_count = [0]

    def save():
        call_count[0] += 1
        if call_count[0] == 2:
            raise IOError("disk full")

    p._save_data = save
    tid = p._register_task(task_type="batch", script_id="s1")
    p._run_per_item_batch(tid, [_Item("a"), _Item("b"), _Item("c")], lambda x: None)
    assert p.asset_generation_tasks[tid]["completed_count"] == 3


# === _run_one_shot ========================================================


def test_one_shot_stashes_result():
    p = _bare_pipeline()
    tid = p._register_task(task_type="oneshot", script_id="s1")
    p._run_one_shot(tid, lambda: {"polished": "hello"})
    task = p.asset_generation_tasks[tid]
    assert task["status"] == "completed"
    assert task["result"] == {"polished": "hello"}


def test_one_shot_failure_no_result_field():
    p = _bare_pipeline()
    tid = p._register_task(task_type="oneshot", script_id="s1")
    p._run_one_shot(tid, lambda: (_ for _ in ()).throw(RuntimeError("LLM down")))
    task = p.asset_generation_tasks[tid]
    assert task["status"] == "failed"
    assert task["error"] == "LLM down"
    # The lifecycle bails before assigning result; status response just omits it.
    assert "result" not in task


# === Status surface =======================================================


def test_status_endpoint_surfaces_one_shot_result():
    p = _bare_pipeline()
    tid = p._register_task(task_type="oneshot", script_id="s1")
    p._run_one_shot(tid, lambda: "polished prompt")
    status = p.get_asset_generation_task_status(tid)
    assert status["result"] == "polished prompt"
    assert status["status"] == "completed"
