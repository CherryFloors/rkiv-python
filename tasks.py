from invoke import task


@task
def test(ctx):
    ctx.run("pytest --cov --cov-fail-under=10", echo=True)


@task
def validate(ctx):
    """validate"""
    ctx.run("pyflakes ./src", echo=True)
    ctx.run("pyflakes ./tests", echo=True)
    ctx.run("black --check --diff  --verbose .", echo=True)

    ctx.run("pylint ./src", warn=True, echo=True)
    ctx.run("pylint ./tests", warn=True, echo=True)

    ctx.run("mypy --install-types --non-interactive ./src", echo=True)
    ctx.run("mypy ./src", echo=True)
    ctx.run("mypy --install-types --non-interactive ./tests", echo=True)
    ctx.run("mypy ./tests", echo=True)


@task
def fmt(ctx):
    ctx.run("black .")
