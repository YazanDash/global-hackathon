from pathlib import Path
import typer

from .agent import CodingAgent
from .config import Settings
from .ledger import Ledger
from .llm import BifrostClient
from .tools.base import Tool, ToolRegistry
from .tools.files import grep, list_files, read_file, read_lines, write_patch
from .tools.tests import run_tests

app = typer.Typer()


def _registry(workspace: Path):
    registry = ToolRegistry()
    common = {"type": "object", "properties": {}}
    registry.register(Tool("list_files", "List workspace files.", common,
                           lambda root=".": list_files(workspace)))
    registry.register(Tool("grep", "Search text files.", {"type": "object", "properties": {
        "pattern": {"type": "string"}, "root": {"type": "string", "default": "."}
    },     "required": ["pattern"]}, lambda pattern, root=".": grep(pattern, workspace)))
    registry.register(Tool("read_file", "Read a text file.", {"type": "object", "properties": {
        "path": {"type": "string"}}, "required": ["path"]},
        lambda path: read_file(path, workspace)))
    registry.register(Tool("read_lines", "Read a line range.", {"type": "object", "properties": {
        "path": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"}},
        "required": ["path", "start", "end"]},
        lambda path, start, end: read_lines(path, start, end, workspace)))
    registry.register(Tool("write_patch", "Apply a unified diff.", {"type": "object", "properties": {
        "diff": {"type": "string"}}, "required": ["diff"]},
        lambda diff: write_patch(diff, workspace)))
    registry.register(Tool("run_tests", "Run pytest and return compressed output.", {"type": "object",
        "properties": {"test_filter": {"type": "string", "default": ""}}},
        lambda test_filter="": run_tests(test_filter or None, workspace)))
    return registry


@app.command()
def run(issue: str = typer.Option(...), workspace: Path = typer.Option(Path(".")),
        max_tokens: int | None = typer.Option(None), model: str | None = typer.Option(None)):
    settings = Settings.from_env()
    if model:
        settings.coder_model = model
    target = workspace.resolve()
    ledger = Ledger(settings.ledger_path)
    agent = CodingAgent(BifrostClient(settings.bifrost_base_url, settings.bifrost_api_key),
                        _registry(target), ledger, settings)
    result = agent.run(issue, max_tokens)
    summary = ledger.summary()
    typer.echo("BudgetDev run complete")
    typer.echo(f"Success: {str(result.success).lower()}")
    typer.echo(f"Steps used: {result.steps_used}")
    typer.echo(f"Total tokens: {result.total_tokens}")
    typer.echo(f"LLM calls: {summary['llm_calls']}")
    typer.echo(f"Tool calls: {summary['tool_calls']}")
    typer.echo(f"Stopped reason: {result.stopped_reason}")
    if result.final_message:
        typer.echo(f"Message: {result.final_message}")
    if result.patch:
        typer.echo(result.patch)


@app.command()
def report():
    typer.echo(Ledger(Settings.from_env().ledger_path).summary())


@app.command()
def test(filter: str | None = typer.Option(None, "--filter")):
    typer.echo(run_tests(filter))
