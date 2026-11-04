"""Execute the installed MetricFlow console script with local-only settings.

Run with the pinned MetricFlow environment's Python, never import in the host.
"""
import runpy
import sys


def _deny_sockets(event, _arguments):
    if event.startswith("socket."):
        raise PermissionError("Network disabled for MetricFlow worker")


def _record_executed_sql():
    from metricflow.engine.metricflow_engine import MetricFlowEngine

    query = MetricFlowEngine.query

    def record(self, *args, **kwargs):
        result = query(self, *args, **kwargs)
        # Same normalization as SqlStatement.without_descriptions in
        # MetricFlow 0.213.0. The result carries SQL from the execution task.
        print("\n".join(line for line in result.sql.split("\n")
                        if not line.strip().startswith("--")))
        return result

    MetricFlowEngine.query = record


if __name__ == "__main__":
    sys.addaudithook(_deny_sockets)
    import update_checker

    # dbt-metricflow 0.15.0 attempts a PyPI lookup even for local queries.
    update_checker.UpdateChecker.check = lambda *_args, **_kwargs: None
    sys.argv = sys.argv[1:]
    if sys.argv[1:2] == ["query"] and "--explain" not in sys.argv:
        _record_executed_sql()
    runpy.run_path(sys.argv[0], run_name="__main__")
