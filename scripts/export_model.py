"""Export a YOLO model to ONNX format for production inference."""

import shutil
from pathlib import Path

import typer
from ultralytics import YOLO

app = typer.Typer(help="YOLO model export utilities.")


@app.command()
def export(
    model: str = typer.Option(
        "yolo11n", help="YOLO model name (e.g. yolo11n, yolo11s)"
    ),
    output_dir: Path = typer.Option(
        Path(".data"), help="Directory to save the exported ONNX model"
    ),
    force: bool = typer.Option(False, help="Overwrite existing ONNX file"),
) -> None:
    """Download YOLO weights and export to ONNX format."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / f"{model}.onnx"

    if dest.exists() and not force:
        typer.echo(f"ONNX model already exists at {dest}. Use --force to overwrite.")
        raise typer.Exit(code=1)

    typer.echo(f"Loading model: {model}")
    yolo = YOLO(f"{model}.pt")

    typer.echo("Exporting to ONNX format...")
    exported_path = yolo.export(format="onnx")
    exported = Path(exported_path)

    shutil.move(str(exported), str(dest))
    typer.echo(f"ONNX model saved to: {dest}")

    pt_file = Path(f"{model}.pt")
    if pt_file.exists():
        pt_file.unlink()
        typer.echo(f"Cleaned up weights file: {pt_file}")


if __name__ == "__main__":
    app()
