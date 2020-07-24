# Copyright © 2020 IBM
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, yaml, json, csv, os.path

from datetime import datetime
from calendar import monthrange

from client import GHClient

VERBOSE=False

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Console:
    def verbose(msg):
        if VERBOSE:
            print(f"{Colors.OKBLUE}{msg}{Colors.ENDC}".format(msg=str(msg)))

    def print(msg=''):
        print(msg)

    def ok(msg):
        print(f"{Colors.OKGREEN}{msg}{Colors.ENDC}".format(msg=str(msg)))

    def fail(msg):
        print(f"{Colors.FAIL}Error: {msg}{Colors.ENDC}".format(msg=str(msg)))

    def warn(msg):
        print(f"{Colors.WARNING}Warning: {msg}{Colors.ENDC}".format(msg=str(msg)))

    def progress(count, total, status=''):
        bar_len = 60
        filled_len = int(round(bar_len * count / float(total)))

        percents = round(100.0 * count / float(total), 1)
        bar = '=' * filled_len + '-' * (bar_len - filled_len)

        sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
        sys.stdout.flush()

def parse_credentials_map(file_name):
    credentials_map = {'access_token': ''}
    try:
        with open(file_name) as file:
            loaded_credentials = yaml.load(file, Loader=yaml.FullLoader)
            credentials_map.update(loaded_credentials)
    except:
        Console.fail("opening credentials file: {file_name}".format(file_name=file_name))
    return credentials_map

class Credentials:
    def __init__(self, hash):
        self.hash = hash

    def access_token(self):
        return self.hash['access_token']

class CLI:
    def __init__(self, args):
        self.args = args
        self.credentials = self.__setup_credentials()
        if self.args['--verbose']:
            VERBOSE = True

    def __parse_credentials(self):
        file_name = '.ghtrack.yml'
        if '--credentials' in self.args: file_name = self.args['--credentials']
        return parse_credentials_map(file_name)

    def __setup_credentials(self):
        credentials_hash = self.__parse_credentials()
        if self.args['--access-token']:
            credentials_hash['access_token'] = self.args['--access-token']
        else:
            self.args['--access-token'] = credentials_hash['access_token']
        return Credentials(credentials_hash)

    def command(self, client=None):
        if client == None:
            client = GHClient(self.credentials.access_token())
        if self.args.get('commits') and self.args['commits']:
            return Commits(self.args, self.credentials, client)
        elif self.args.get('reviews') and self.args['reviews']:
            return Reviews(self.args, self.credentials, client)
        elif self.args.get('prs') and self.args['prs']:
            return PRs(self.args, self.credentials, client)
        elif self.args.get('issues') and self.args['issues']:
            return Issues(self.args, self.credentials, client)
        elif self.args.get('stats') and self.args['stats']:
            return Stats(self.args, self.credentials, client)
        else:
            raise Exception("Invalid command")

class Command:
    LIST_OPTIONS = ['--users', '--repos', '--skip-repos']
    MONTHS_CAP = {'January':1, 'February':2, 'March':3, 'April':4, 'May':5, 'June':6, 'July':7, 'August':8, 'September':9, 'October':10, 'November':11, 'December':12}
    MONTHS_LOWER = {'january':1, 'february':2, 'march':3, 'april':4, 'may':5, 'june':6, 'july':7, 'august':8, 'september':9, 'october':10, 'november':11, 'december':12}
    MONTHS_UPPER = {'JANUARY':1, 'FEBRUARY':2, 'MARCH':3, 'APRIL':4, 'MAY':5, 'JUNE':6, 'JULY':7, 'AUGUST':7, 'SEPTEMBER':9, 'OCTOBER':10, 'NOVEMBER':11, 'DECEMBER':12}
    MONTHS_ABREV = {'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6, 'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec':12}
    def __init__(self, args, credentials, client):
        self.__init_empty_options(args)
        self.args = args
        self.credentials = credentials
        self.client = client
        self.__month_number = 0

    def __init_empty_options(self, args):
        for option in self.LIST_OPTIONS:
            if args[option] == None or args[option] == '':
                args[option] = []
            elif isinstance(args[option], str):
                if ',' in args[option]:
                    args[option] = args[option].split(',')
                else:
                    args[option] = [args[option]]

    def _init_users_stats(self, users_stats):
        for user in self.users():
            users_stats[user] = {}
            for repo in self.repos():
                if repo not in self.skip_repos():
                    users_stats[user][repo] = 0

    def check_month(self, month):
        if month in self.MONTHS_LOWER.keys():
            self.__month_number = self.MONTHS_LOWER[month]
            return True
        elif month in self.MONTHS_UPPER.keys():
            self.__month_number = self.MONTHS_UPPER[month]
            return True
        elif month in self.MONTHS_CAP.keys():
            self.__month_number = self.MONTHS_CAP[month]
            return True
        elif month in self.MONTHS_ABREV.keys():
            self.__month_number = self.MONTHS_ABREV[month]
            return True
        return False

    def check_org(self, org):
        if org == None:
            return False
        elif org == '':
            return False
        return True

    def check_required_options(self):
        if not self.check_month(self.month()):
            self.print("Invalid month '{month}'".format(month=self.month()))
            return False
        elif not self.check_org(self.org()):
            self.print("Invalid org value '{org}'".format(org=self.org()))
            return False
        return True

    def println(self, msg):
        self.print(msg + "\n")

    def print(self, msg):
        Console.print(msg)

    def warn(self, msg):
        Console.warn(msg)

    def verbose(self):
        return self.args['--verbose']

    def year(self):
        return datetime.now().year

    def start_date(self):
        return datetime(month=self.month_number(), day=1, year=self.year())

    def end_date(self):
        return datetime(month=self.month_number(), day=self.month_last_day(), year=self.year())

    def month_last_day(self):
        range = monthrange(self.year(), self.month_number())
        return range[1]

    def month_number(self):
        return self.__month_number

    def month(self):
        return self.args['MONTH']

    def users(self):
        return self.args['--users']

    def org(self):
        return self.args['ORG']

    def repos(self):
        return self.args['--repos']

    def skip_repos(self):
        return self.args['--skip-repos']

    def all_repos(self):
        return self.args['--all-repos']

    def cmd_line(self):
        repos_line = "--all-repos"
        if self.args['--all-repos'] == False:
            repos_line = "--repos={repos} --skip-repos={skip_repos}".format(repos=','.join(self.repos()), skip_repos=','.join(self.skip_repos()))
        cmd_line = "{name} {month} {org} --users={users}".format(name=self.name(), month=self.month(), users=','.join(self.users()), org=self.org())
        cmd_line += " " + repos_line
        return cmd_line

    def start_comment(self):
        Console.verbose("# GH Track output for cmd line: {cmd_line}".format(cmd_line=self.cmd_line()))

    def fetch_repos(self):
        if not self.all_repos(): return
        if self.all_repos() and len(self.repos()) > 0:
            self.warn("ignoring --repos since --all-repos is set")
        repo_names = []
        repos = self.client.repos(self.org())
        for repo in repos: repo_names.append(repo.name)
        self.args['--repos'] = repo_names

    def output(self, output_map):
        Console.print()
        text_output = json.dumps(output_map, indent=4, sort_keys=True)
        Console.print(text_output)
        Console.ok("OK")

    def execute(self):
        self.fetch_repos()
        if not self.check_required_options():
            return -1
        func = self.dispatch()
        rc = func()
        if rc == None:
            return 0
        else:
            if isinstance(rc, int):
                return rc
            else:
                return -1

    def dispatch(self):
        if self.args['commits']:
            return self.commits
        elif self.args['reviews']:
            return self.reviews
        elif self.args['prs']:
            return self.prs
        elif self.args['issues']:
            return self.issues
        elif self.args['stats']:
            return self.stats
        else:
            raise Exception("Invalid subcommand")

# commits command group
class Commits(Command):
    def __init__(self, args, credentials, client):
        self.args = args
        self.users_commits = {} # {user: {repo_name: commit_count},...}
        super().__init__(self.args, credentials, client)
        self._init_users_stats(self.users_commits)

    def __print(self, commit):
        print("Commits: {args}".format(args=self.args))

    def name(self):
      return "commits"

    def commits(self):
        self.start_comment()
        Console.warn("getting commits for {total_users} users in {total_repos} repos via GitHub APIs... be patient".format(total_users=len(self.users()), total_repos=len(self.repos())))
        for user in self.users():
            repos = self.client.repos(self.org())
            count, total = 1, repos.totalCount
            for repo in repos:
                Console.progress(count, total, status="processing repos".format(name=repo.name))
                if repo.name in self.repos() and repo.name not in self.skip_repos():
                    commits_count = self.client.commits_count(repo, user, self.start_date(), self.end_date())
                    self.users_commits[user][repo.name] = commits_count
                count += 1
        self.output(self.users_commits)
        return 0

# reviews command group
class Reviews(Command):
    def __init__(self, args, credentials, client):
        self.args = args
        self.users_reviews = {} # {user: {repo_name: review_count},...}
        super().__init__(self.args, credentials, client)
        self._init_users_stats(self.users_reviews)

    def __print(self, commit):
        print("Reviews: {args}".format(args=self.args))

    def name(self):
      return "reviews"

    def reviews(self): 
        self.start_comment()
        Console.warn("getting reviews for {total_users} users in {total_repos} repos via GitHub APIs... be patient".format(total_users=len(self.users()), total_repos=len(self.repos())))
        for user in self.users():
            repos = self.client.repos(self.org())
            count, total = 1, repos.totalCount
            for repo in repos:
                Console.progress(count, total, status="processing repos".format(name=repo.name))
                if repo.name in self.repos() and repo.name not in self.skip_repos():
                    reviews_count = self.client.reviews_count(repo, user, self.start_date(), self.end_date())
                    self.users_reviews[user][repo.name] = reviews_count
                count += 1
        self.output(self.users_reviews)
        return 0

# prs command group
class PRs(Command):
    def __init__(self, args, credentials, client):
        self.args = args
        self.users_prs = {} # {user: {repo_name: pr_count},...}
        super().__init__(self.args, credentials, client)
        self._init_users_stats(self.users_prs)

    def __print(self, commit):
        print("PRs: {args}".format(args=self.args))

    def name(self):
      return "prs"

    def prs(self):
        self.start_comment()
        Console.warn("getting prs for {total_users} users in {total_repos} repos via GitHub APIs... be patient".format(total_users=len(self.users()), total_repos=len(self.repos())))
        for user in self.users():
            repos = self.client.repos(self.org())
            count, total = 1, repos.totalCount
            for repo in repos:
                Console.progress(count, total, status="processing repos".format(name=repo.name))
                if repo.name in self.repos() and repo.name not in self.skip_repos():
                    prs_count = self.client.prs_count(repo, user, self.start_date(), self.end_date(), 'open')
                    self.users_prs[user][repo.name] = prs_count
                count += 1
        self.output(self.users_prs)
        return 0

# issues command group
class Issues(Command):
    def __init__(self, args, credentials, client):
        self.args = args
        self.users_issues = {} # {user: {repo_name: issue_count},...}
        super().__init__(self.args, credentials, client)
        self._init_users_stats(self.users_issues)

    def __print(self, commit):
        print("Issues: {args}".format(args=self.args))

    def name(self):
      return "issues"

    def issues(self):
        self.start_comment()
        Console.warn("getting issues for {total_users} users in {total_repos} repos via GitHub APIs... be patient".format(total_users=len(self.users()), total_repos=len(self.repos())))
        for user in self.users():
            repos = self.client.repos(self.org())
            count, total = 1, repos.totalCount
            for repo in repos:
                Console.progress(count, total, status="processing repos".format(name=repo.name))
                if repo.name in self.repos() and repo.name not in self.skip_repos():
                    issues_count = self.client.issues_count(repo, user, self.start_date(), self.end_date(), 'open')
                    self.users_issues[user][repo.name] = issues_count
                count += 1
        self.output(self.users_issues)
        return 0

# stats command group
class Stats(Command):
    def __init__(self, args, credentials, client):
        self.args = args
        super().__init__(self.args, credentials, client)

    def __print(self, commit):
        print("Stats: {args}".format(args=self.args))

    def name(self):
      return "stats"

    def stats(self):
        self.start_comment()
        return 0
