# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This file defines classes for events which are sent by GitHub or FedMsg.
"""
import enum

from ogr.abstract import GitProject
from ogr.services.pagure import PagureService
from packit.config import (
    JobTriggerType,
    get_package_config_from_repo,
    PackageConfig,
    Config,
)
from packit.ogr_services import get_github_project


class PullRequestAction(enum.Enum):

    opened = "opened"
    reopened = "reopened"
    synchronize = "synchronize"


class FedmsgTopic(enum.Enum):
    dist_git_push = "org.fedoraproject.prod.git.receive"
    copr_build_finished = "org.fedoraproject.prod.copr.build.end"
    pr_flag_added = "org.fedoraproject.prod.pagure.pull-request.flag.added"


class WhitelistStatus(enum.Enum):
    approved_automatically = "approved_automatically"
    waiting = "waiting"
    approved_manually = "approved_manually"


class Event:
    def __init__(self, trigger: JobTriggerType):
        self.trigger: JobTriggerType = trigger


class ReleaseEvent(Event):
    def __init__(
        self, repo_namespace: str, repo_name: str, tag_name: str, https_url: str
    ):
        super(ReleaseEvent, self).__init__(JobTriggerType.release)
        self.repo_namespace = repo_namespace
        self.repo_name = repo_name
        self.tag_name = tag_name
        self.https_url = https_url

    def get_dict(self) -> dict:
        result = self.__dict__
        result["trigger"] = str(result["trigger"])
        return result

    def get_package_config(self):
        package_config: PackageConfig = get_package_config_from_repo(
            self.get_project(), self.tag_name
        )
        package_config.upstream_project_url = self.https_url
        return package_config

    def get_project(self) -> GitProject:
        return get_github_project(
            Config.get_user_config(), repo=self.repo_name, namespace=self.repo_namespace
        )


class PullRequestEvent(Event):
    def __init__(
        self,
        action: PullRequestAction,
        pr_id: int,
        base_repo_namespace: str,
        base_repo_name: str,
        base_ref: str,
        target_repo: str,
        https_url: str,
        commit_sha: str,
    ):
        super(PullRequestEvent, self).__init__(JobTriggerType.pull_request)
        self.action = action
        self.pr_id = pr_id
        self.base_repo_namespace = base_repo_namespace
        self.base_repo_name = base_repo_name
        self.base_ref = base_ref
        self.target_repo = target_repo
        self.https_url = https_url
        self.commit_sha = commit_sha

    def get_dict(self) -> dict:
        result = self.__dict__
        # whole dict have to be JSON serializable because of redis
        result["trigger"] = str(result["trigger"])
        result["action"] = str(result["action"])
        return result

    def get_package_config(self):
        package_config: PackageConfig = get_package_config_from_repo(
            self.get_project(), self.base_ref
        )
        package_config.upstream_project_url = self.https_url
        return package_config

    def get_project(self) -> GitProject:
        return get_github_project(
            Config.get_user_config(),
            repo=self.base_repo_name,
            namespace=self.base_repo_namespace,
        )


class InstallationEvent(Event):
    def __init__(
        self,
        installation_id: int,
        account_login: str,
        account_id: int,
        account_url: str,
        account_type: str,
        created_at: int,
        sender_id: int,
        sender_login: str,
        status: WhitelistStatus = WhitelistStatus.waiting,
    ):
        super(InstallationEvent, self).__init__(JobTriggerType.installation)
        self.installation_id = installation_id
        self.account_login = account_login
        self.account_id = account_id
        self.account_url = account_url
        self.account_type = account_type
        self.created_at = created_at
        self.sender_id = sender_id
        self.sender_login = sender_login
        self.status = status

    def get_dict(self) -> dict:
        result = self.__dict__
        # whole dict have to be JSON serializable because of redis
        result["trigger"] = str(result["trigger"])
        result["status"] = str(result["status"])
        return result


class DistGitEvent(Event):
    def __init__(
        self,
        topic: FedmsgTopic,
        repo_namespace: str,
        repo_name: str,
        ref: str,
        branch: str,
        msg_id: str,
    ):
        super(DistGitEvent, self).__init__(JobTriggerType.commit)
        self.topic = topic
        self.repo_namespace = repo_namespace
        self.repo_name = repo_name
        self.ref = ref
        self.branch = branch
        self.msg_id = msg_id

    def get_dict(self) -> dict:
        result = self.__dict__
        # whole dict have to be JSON serializable because of redis
        result["trigger"] = str(result["trigger"])
        result["topic"] = str(result["topic"])
        return result

    def get_package_config(self):

        return get_package_config_from_repo(self.get_project(), self.ref)

    def get_project(self) -> GitProject:
        config = Config.get_user_config()
        pagure_service = PagureService(
            token=config.pagure_user_token,
            read_only=config.dry_run,
            # TODO: how do we change to stg here? ideally in self.config
        )
        return pagure_service.get_project(
            repo=self.repo_name, namespace=self.repo_namespace
        )
