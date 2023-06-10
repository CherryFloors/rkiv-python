from invoke import task

@task
def test(ctx):
    ctx.run("pytest --cov")

@task
def fmt(ctx):
    ctx.run("black src")