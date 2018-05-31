from urllib.parse import urlparse
import urllib
import collections

file='/home/will/work/kayobe-overcloud-deploy'

pip_pkgs = set()
yum_pkgs = set()
docker_images = set()
galaxy_roles = set()
galaxy = set()
raw = set()
git = set()

pip_paths = {"pypi.org", "pypi.python.org"}

def parse_pip(agent, url, path):
    if not agent.startswith("pip") and not agent.startswith("setuptools"):
        return False
    if url.netloc in pip_paths:
        pkg = path[-1]
        pip_pkgs.add(pkg)
        return True
    if url.netloc != "files.pythonhosted.org":
        # suupose to be requirement files
        # eg https://raw.githubusercontent.com/openstack/requirements/stable/queens/upper-constraints.txt
        raw.add(url.geturl())
        return True
    # ignore rest
    return True

def parse_yum(agent, url, path):
    if not agent.startswith("urlgrabber"):
        return False
    if not url.path.endswith("rpm"):
        return False
    yum_pkgs.add(path[-1])
    return True

def parse_docker(agent, url, path):
    if not agent.startswith("docker"):
        return False
    if url.netloc != "registry-1.docker.io":
        return True
    if len(path) < 4:
        return True
    docker_images.add("{}/{}".format(path[2], path[3]))
    return True

def parse_galaxy(agent, url, path):
    if url.netloc != "galaxy.ansible.com":
        return False
    query = urllib.parse.parse_qs(url.query)
    if "name" not in query:
        return False
    if isinstance(query["name"], collections.Iterable):
        for x in query["name"]:
            galaxy_roles.add(x)
    else:
        galaxy_roles.add(query["name"])

    return True

def parse_git(agent, url, path):
    if not agent.startswith("git"):
        return False
    if url.path.endswith("/info/refs"):
        path = "/".join(path[:-2])
        url2 = url._replace(path=path, query="")
        git.add(url2.geturl())
    # swallow rest?
    return True

def parse_raw(agent, url, path):
    if agent.startswith("ansible-httpget"):
        raw.add(url.geturl())
        return True


with open(file, "r") as file:
    parsers = [parse_pip, parse_yum, parse_docker,parse_galaxy, parse_git, parse_raw]
    for line in file.readlines():
        chunks = line.split(" ")
        agent = chunks[-1]
        url_str = chunks[1]
        url = urlparse(url_str)
        path = url.path.rstrip("/").split("/")
        for parser in parsers:
            if parser(agent, url, path):
                break
        else:
            print(agent)
            print(url_str)
        #print(agent)
        #print(url)


# print("pip: ")
# for pkg in pip_pkgs:
#    print(pkg)
#
# print("yum: ")
# for pkg in yum_pkgs:
#     print(pkg)
# print("yum: ")
for pkg in git:
    print(pkg)