import typer

from model_100.cli import app as renta_app
from model_720.cli import app as modelo720_app

app = typer.Typer(
    add_completion=False,
    help="Herramientas fiscales (España): Declaracion Renta (Modelo 100) + modelo 720.",
)
app.add_typer(renta_app, name="modelo-100")
app.add_typer(modelo720_app, name="modelo-720")

if __name__ == "__main__":
    app()
