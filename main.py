import os
import requests
import json
from pathlib import Path
import hashlib


def create_path_for_file_if_not_exists(file_path):
    file_directory = os.path.dirname(file_path)
    Path(file_directory).mkdir(parents=True, exist_ok=True)


class GitHubReleaseInfoDownloader:

    @staticmethod
    def construct_if_modified_headers(modified_since=None, etag=None):
        headers = {}
        if etag is not None:
            headers.update({"If-None-Match": etag})
        elif modified_since is not None:
            headers.update({"If-Modified-Since": modified_since})
        return headers

    @staticmethod
    def load_if_modified_headers_from_cache(cache_file):
        try:
            with open(cache_file, 'r') as json_file:
                data = json.load(json_file)
                # print("read cache file: " + cache_file)
                return GitHubReleaseInfoDownloader.construct_if_modified_headers(data.get('Last-Modified', None), data.get('ETag', None))
        except FileNotFoundError:
            # No need to worry - cache file doesn't exist
            pass
        except IOError as e:
            print("Unexpected I/O error({0}): {1}".format(e.errno, e.strerror))
        return {}

    @staticmethod
    def save_if_modified_headers_to_cache(cache_file, headers):
        saved_headers = {}
        etag = headers.get('ETag', None)
        last_modified = headers.get('Last-Modified', None)
        if etag is not None:
            saved_headers.update({"ETag": etag})
        if last_modified is not None:
            saved_headers.update({"Last-Modified": last_modified})
        create_path_for_file_if_not_exists(cache_file)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(saved_headers, f, ensure_ascii=False, indent=4)

    def release_sanitizer(self, release):
        if len(self.filter_release_keys) > 0:
            # Remove the specified fields from the release:
            [release.pop(k) for k in list(release.keys()) if k in self.filter_release_keys]
        if len(self.filter_asset_keys) > 0:
            # Remove the specified fields from each asset:
            for n, asset in enumerate(release['assets']):
                [asset.pop(k) for k in list(asset.keys()) if k in self.filter_asset_keys]
                release['assets'][n] = asset

        return release

    def filter_release(self, release):
        # Remove all draft (non-public) releases
        if self.filter_draft_releases:
            is_draft = release.get('draft', None)
            if is_draft is not None and is_draft is True:
                return True

        # Otherwise, keep this entry
        return False

    def releases_sanitizer(self, releases):
        releases[:] = [release for release in releases if not self.filter_release(release)]

        for n, release in enumerate(releases):
            # Sanitize release information
            releases[n] = self.release_sanitizer(release)

        return releases

    def calculate_assets_info(self, session, release):
        # For each asset:
        for n, asset in enumerate(release['assets']):
            # Download the asset, calculate hashes
            url = asset['url']
            headers = {"Accept": "application/octet-stream"}

            sha256 = hashlib.sha256()
            sha512 = hashlib.sha512()
            blake2b = hashlib.blake2b()
            with session.get(url, headers=headers, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        sha256.update(chunk)
                        sha512.update(chunk)
                        blake2b.update(chunk)

            asset['sha256'] = sha256.hexdigest()
            asset['sha512'] = sha512.hexdigest()
            asset['blake2b'] = blake2b.hexdigest()

            release['assets'][n] = asset

        return release

    def get_release(self, session, release_id, output_file_extension='json', calculate_asset_info=False):
        url = "https://api.github.com/repos/"+self.github_repo+"/releases/"+release_id
        output_filename = release_id
        # store the last-modified / etag headers for a request inside a cache file alongside
        cache_filename = os.path.sep.join([self.cache_directory, output_filename])
        headers = GitHubReleaseInfoDownloader.load_if_modified_headers_from_cache(cache_filename)

        response = session.get(url, headers=headers)

        if response.status_code == 304:
            # Not Modified Since Last Requested
            # nothing more to do
            print("Not Modified: release ({})".format(release_id))
            return True
        elif response.status_code != 200:
            # Failure to retrieve data
            print("Failed to retrieve release ({}) with status_code: {}".format(release_id, response.status_code))
            return False

        release = response.json()

        # Sanitize response (as desired)
        release = self.release_sanitizer(release)

        if calculate_asset_info is True:
            release = self.calculate_assets_info(session, release)

        # Save response
        output_filename = os.path.sep.join([self.output_directory, output_filename])
        create_path_for_file_if_not_exists(output_filename)
        with open(output_filename+"."+output_file_extension, 'w', encoding='utf-8') as f:
            json.dump(release, f, ensure_ascii=False, indent=4)

        # Save cache information about response (last-modified, etc)
        GitHubReleaseInfoDownloader.save_if_modified_headers_to_cache(cache_filename, response.headers)

        return True

    def get_releases(self, session, limit_pages=0):
        url = "https://api.github.com/repos/"+self.github_repo+"/releases"
        response = session.get(url, allow_redirects=True)

        releases = response.json()
        print(response.headers)

        if response.status_code != 200:
            print("Failed to retrieve releases list with status_code: {}".format(response.status_code))
            return None

        if not isinstance(releases, (list, tuple)):
            print("Unexpected type returned from parsing releases list JSON: {}".format(type(releases)))
            print(releases)
            return None

        curr_page_num = 1
        while ('next' in response.links.keys()) and ((limit_pages == 0) or (curr_page_num < limit_pages)):
            print('- Fetching page ({}): {}'.format(curr_page_num, response.links['next']['url']))
            response = session.get(response.links['next']['url'], allow_redirects=True)
            print(response.headers)

            if response.status_code != 200:
                print("Failed to retrieve releases list (page: {}) with status_code: {}".format(curr_page_num, response.status_code))
                return None

            if not isinstance(releases, (list, tuple)):
                print("Unexpected type returned from parsing releases list (page: {}) JSON: {}".format(curr_page_num, type(releases)))
                print(releases)
                return None

            releases.extend(response.json())
            curr_page_num += 1

        return self.releases_sanitizer(releases)

    def __init__(self, github_repo, output_directory, cache_directory, filter_draft_releases, filter_release_keys, filter_asset_keys):
        self.github_repo = github_repo
        self.output_directory = output_directory
        self.cache_directory = cache_directory
        self.filter_draft_releases = filter_draft_releases
        self.filter_release_keys = filter_release_keys
        self.filter_asset_keys = filter_asset_keys


def main():
    github_repo = os.getenv("INPUT_GITHUB_REPO", default=os.getenv("GITHUB_REPOSITORY", default=None))
    if github_repo is None:
        print("::error ::Missing required github_repo input (neither INPUT_GITHUB_REPO nor GITHUB_REPOSITORY were present)!")
        exit(1)
    print("For Github Repo: " + github_repo)
    github_token = os.getenv("INPUT_GITHUB_TOKEN", default=None)
    github_release_id = os.getenv("INPUT_GITHUB_RELEASE_ID", default="latest")
    output_directory = os.getenv("INPUT_OUTPUT_DIRECTORY", default="releases")
    cache_directory = os.getenv("INPUT_CACHE_DIRECTORY", default="_cache_data/releases")
    output_file_extension = os.getenv("INPUT_OUTPUT_FILE_EXTENSION", default="json")
    fetch_release_index = os.getenv("INPUT_FETCH_RELEASE_INDEX", default="false") == "true"
    filter_draft_releases = os.getenv("INPUT_FILTER_DRAFT_RELEASES", default="true") == "true"
    filter_release_keys_str = os.getenv("INPUT_FILTER_RELEASE_KEYS", default='["author"]')
    filter_asset_keys_str = os.getenv("INPUT_FILTER_ASSET_KEYS", default='["uploader", "download_count"]')
    calculate_asset_info = os.getenv("INPUT_CALCULATE_ASSET_INFO", default="false") == "true"

    output_directory = os.path.normpath(output_directory)
    cache_directory = os.path.normpath(cache_directory)

    # parse filter_(release/asset)_info (expecting: json array of strings, or "false")
    filter_release_keys_list = []
    filter_asset_keys_list = []
    try:
        if filter_release_keys_str != "false":
            filter_release_keys_list = json.loads(filter_release_keys_str)
        if filter_asset_keys_str != "false":
            filter_asset_keys_list = json.loads(filter_asset_keys_str)
    except ValueError:
        raise
    filter_release_keys = set(filter_release_keys_list)
    filter_asset_keys = set(filter_asset_keys_list)

    session = requests.Session()

    # If specified, set up authorization with GITHUB_TOKEN (increases rate limits)
    if github_token is not None:
        session.headers.update({"Authorization": "token " + github_token})

    Path(output_directory).mkdir(parents=True, exist_ok=True)

    fetcher = GitHubReleaseInfoDownloader(github_repo, output_directory, cache_directory, filter_draft_releases, filter_release_keys, filter_asset_keys)

    if (fetch_release_index):
        print("Fetching index of releases")
        releases = fetcher.get_releases(session)
        if releases is not None:
            with open((os.path.sep.join([output_directory, 'index']) + "." + output_file_extension), 'w', encoding='utf-8') as f:
                json.dump(releases, f, ensure_ascii=False, indent=4)

    print("Fetching information on specific GitHub release_id: " + github_release_id)
    fetcher.get_release(session, github_release_id, output_file_extension, calculate_asset_info)


if __name__ == "__main__":
    main()
