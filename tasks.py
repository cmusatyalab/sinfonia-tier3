# SPDX-FileCopyrightText: 2022 Carnegie Mellon University
# SPDX-License-Identifier: 0BSD

# pyinvoke file for maintenance tasks

import re

from invoke import task


@task
def update_dependencies(c):
    """Update python package dependencies"""
    # update project + pre-commit check dependencies
    c.run("poetry update")
    c.run("poetry run pre-commit autoupdate")
    # make sure project still passes pre-commit and unittests
    c.run("poetry run pre-commit run -a")
    c.run("poetry run pytest")
    # commit updates
    c.run("git commit -m 'Update dependencies' poetry.lock .pre-commit-config.yaml")


def get_current_version(c):
    """Get the current application version.
    Helm chart version should always be >= application version.
    """
    r = c.run("poetry run tbump current-version", hide="out")
    return r.stdout.strip()


def bump_current_version(c, part):
    """Simplistic version bumping."""
    current_version = get_current_version(c)
    major, minor, patch = re.match(r"(\d+)\.(\d+)\.(\d+)", current_version).groups()
    if part == "major":
        return f"{int(major)+1}.0.0"
    if part == "minor":
        return f"{major}.{int(minor)+1}.0"
    return f"{major}.{minor}.{int(patch)+1}"


@task
def build_release(c, part="patch"):
    """Bump application version, build test release and add a signed tag"""
    release = bump_current_version(c, part)
    c.run(f"poetry run tbump --no-tag --no-push {release}")
    c.run("poetry build")
    c.run(f"git tag -m v{release} v{release}")


@task
def publish(c):
    """Publish application, bump version to dev and push release tags"""
    c.run("poetry publish --build")
    new_version = get_current_version(c) + ".post.dev0"
    c.run(f"poetry run tbump --no-tag --no-push {new_version}")
    c.run("git push")
    c.run("git push --tags")
