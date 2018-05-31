from urllib.parse import urlparse
import urllib
import collections
import fileinput
import argparse


pip_paths = {"pypi.org", "pypi.python.org"}

def parse_pip(agent, url, path, process):
    if not agent.startswith("pip") and not agent.startswith("setuptools"):
        return False
    if url.netloc in pip_paths:
        pkg = path[-1]
        process(pkg)
        return True
    if url.netloc != "files.pythonhosted.org":
        # suupose to be requirement files
        # eg https://raw.githubusercontent.com/openstack/requirements/stable/queens/upper-constraints.txt
        process(url.geturl())
        return True
    # ignore rest
    return True

def parse_yum(agent, url, path, process):
    # FIXME: includes version
    if not agent.startswith("urlgrabber"):
        return False
    if not url.path.endswith("rpm"):
        return False
    process(path[-1])
    return True

def parse_docker(agent, url, path, process):
    if not agent.startswith("docker"):
        return False
    if url.netloc != "registry-1.docker.io":
        return True
    if len(path) < 4:
        return True
    process("{}/{}".format(path[2], path[3]))
    return True

def parse_galaxy(agent, url, path, process):
    if url.netloc != "galaxy.ansible.com":
        return False
    query = urllib.parse.parse_qs(url.query)
    if "name" not in query:
        return False
    if isinstance(query["name"], collections.Iterable):
        for x in query["name"]:
            process(x)
    else:
        process(query["name"])

    return True

def parse_git(agent, url, path, process):
    if not agent.startswith("git"):
        return False
    if url.path.endswith("/info/refs"):
        path = "/".join(path[:-2])
        url2 = url._replace(path=path, query="")
        process(url2.geturl())
    # swallow rest?
    return True

def parse_raw(agent, url, path, process):
    # FIXME: missing stuff... use blacklist?
    if agent.startswith("ansible-httpget"):
        process(url.geturl())
        return True

def swallow(parser):
    return lambda agent, url, path: parser(agent, url, path, lambda _: None)

def print_result(parser):
    return lambda agent, url, path: parser(agent, url, path, lambda x: print(x))


if __name__ == '__main__':
    # ordered so we reduce stuff reaching parse_raw
    parsers = ["parse_pip", "parse_yum", "parse_docker", "parse_galaxy",
               "parse_git", "parse_raw"]

    parser = argparse.ArgumentParser()
    parser.add_argument('parser', choices=parsers, help='parser to run')
    parser.add_argument('files', metavar='FILE', nargs='*', help='files to read, if empty, stdin is used')
    args = parser.parse_args()

    # default swallow the parse result
    decorated_parsers = dict([(x, swallow(globals()[x])) for x in parsers])
    selected = args.parser
    decorated_parsers[selected] = print_result(globals()[selected])

    for line in fileinput.input(files=args.files if len(args.files) > 0 else ('-', )):
        chunks = line.split(" ")
        agent = chunks[-1]
        url_str = chunks[1]
        url = urlparse(url_str)
        path = url.path.rstrip("/").split("/")
        for parser in parsers:
            if decorated_parsers[parser](agent, url, path):
                break