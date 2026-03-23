"""DBOS workflows."""

from dbos import DBOS


@DBOS.workflow()
def dummy_workflow(name: str):
    result = dummy_step(name)
    return result


@DBOS.step()
def dummy_step(name: str):
    return f"Hello, {name}!"
