from spkg_compose.package import SpkgBuild


def get_git_url(package: SpkgBuild) -> str:
    if package.prepare.url == "%meta.source%":
        return package.meta.source
    return package.prepare.url
