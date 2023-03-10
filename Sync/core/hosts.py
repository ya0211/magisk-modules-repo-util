from typing import Optional
from pathlib import Path
from github import Github, UnknownObjectException
from github.Repository import Repository
from ..file import load_json
from ..log import Log


class Hosts:
    def __init__(self, root_folder: Path, user_name: Optional[str] = None, api_token: Optional[str] = None,
                 *, log_folder: Optional[Path] = None, show_log: bool = True):

        self._log = Log("Sync", log_folder, show_log)
        if user_name is None:
            self._init_local(root_folder)
        else:
            self._init_repo(user_name, api_token)

    def _init_local(self, root_folder: Path):
        hosts_json = root_folder.joinpath("json", "hosts.json")
        if not hosts_json.exists():
            self._log.e(f"no such file: {hosts_json.as_posix()}")
            raise FileNotFoundError("hosts.json: You can find template in [util/template]")
        else:
            self._log.i(f"load hosts: {hosts_json.as_posix()}")

        self._hosts: list = load_json(hosts_json)

        self._log.i(f"number of modules: {self.size}")

    def _init_repo(self, user_name: str, api_token: str):
        self._log.i(f"load hosts: {user_name}")

        self._hosts = list()
        github = Github(login_or_token=api_token)
        user = github.get_user(user_name)
        for repo in user.get_repos():
            try:
                if not self.is_module(repo):
                    continue

                self._log.i(f"get host: {repo.name}")
                is_update_json = False
                try:
                    update_to = repo.get_contents("update.json").download_url
                    self._log.i(f"{repo.name}: include a update.json")
                    is_update_json = True
                except UnknownObjectException:
                    update_to = repo.clone_url

                item = {
                    "id": repo.name,
                    "update_to": update_to,
                    "license": self.get_license(repo)
                }

                if not is_update_json:
                    item["changelog"] = self.get_changelog(repo)

                self._hosts.append(item)
            except BaseException as err:
                msg = "{} " * len(err.args)
                msg = msg.format(*err.args).rstrip()
                self._log.e(f"get host failed: {type(err).__name__}({msg})")

        self._log.i(f"number of modules: {self.size}")

    def get_license(self, repo: Repository) -> str:
        try:
            _license = repo.get_license().license.spdx_id
            if _license == "NOASSERTION":
                _license = "UNKNOWN"
        except UnknownObjectException:
            self._log.w(f"{repo.name}: does not include a license")
            _license = ""

        return _license

    def get_changelog(self, repo: Repository) -> str:
        try:
            changelog = repo.get_contents("changelog.md").download_url
            self._log.i(f"{repo.name}: include a changelog.md")
        except UnknownObjectException:
            changelog = ""

        return changelog

    @staticmethod
    def is_module(repo: Repository):
        try:
            repo.get_contents("module.prop")
            return True
        except UnknownObjectException:
            return False

    @property
    def size(self) -> int:
        return self._hosts.__len__()

    @property
    def modules(self) -> list:
        return self._hosts
