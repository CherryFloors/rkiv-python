import click


from rkiv import __version__


@click.command()
@click.version_option(version=__version__)
def main():
    """rkiv"""
    click.secho("rkiv", fg="green")
    click.echo("Welcome")