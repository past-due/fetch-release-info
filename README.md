# Fetch Release Info

[![license](https://img.shields.io/github/license/past-due/fetch-release-info.svg)](https://github.com/past-due/fetch-release-info/blob/master/LICENSE)
[![Actions Status](https://github.com/past-due/fetch-release-info/workflows/Lint/badge.svg)](https://github.com/past-due/fetch-release-info/actions)
[![Actions Status](https://github.com/past-due/fetch-release-info/workflows/Integration%20Test/badge.svg)](https://github.com/past-due/fetch-release-info/actions)

This is a **GitHub Action** to fetch [**GitHub Releases info**](https://developer.github.com/v3/repos/releases/) and store it as JSON files in a folder.
This action can be combined simply and freely with other actions, such as static site generators that use data files.

The next example step will fetch the [latest GitHub Release info](https://developer.github.com/v3/repos/releases/#get-the-latest-release) for the current repository, filter its data by `filter_release_keys` and `filter_asset_keys`, and output the resulting JSON to **`./releases/latest.json`**.

```yaml
- name: Fetch Latest Release Info
  uses: past-due/fetch-release-info@master
  with:
    # Always specify the github_token to increase rate limits
    github_token: '${{ secrets.GITHUB_TOKEN }}'
    
    # By default, output_directory is 'releases'
    # output_directory: 'releases'
    
    # By default, filter_release_keys removes author information
    # filter_release_keys: '["author"]'
    
    # By default, filter_asset_keys removes uploader and download_count information
    # filter_asset_keys: '["uploader", "download_count"]'
```

## Options

### ⭐️ `github_token`

Specify the `GITHUB_TOKEN` to increase rate limits (not required, but strongly encouraged).

```yaml
github_token: ${{ secrets.GITHUB_TOKEN }}
```

### ⭐️ Specify a different GitHub repository

By default, the action will query the current GitHub repository. If you'd like query information about a different repository, set the `github_repo` option.

For example:

```yaml
- name: Fetch Latest Release Info
  uses: past-due/fetch-release-info@master
  with:
    github_token: '${{ secrets.GITHUB_TOKEN }}'
    github_repo: 'nlohmann/json' # example
```

### ⭐️ Specify an explicit GitHub release

By default, the action will query the "latest" Release. If you'd like query information about a different GitHub Release, set the `github_release_id` option. (See: [REST API v3: Get a single release](https://developer.github.com/v3/repos/releases/#get-a-single-release))

For example:

```yaml
- name: Fetch Latest Release Info
  uses: past-due/fetch-release-info@master
  with:
    github_token: '${{ secrets.GITHUB_TOKEN }}'
    github_repo: 'nlohmann/json' # example
    github_release_id: <INSERT_VALUE_HERE> # see: https://developer.github.com/v3/repos/releases/#get-a-single-release
```

### ⭐️ Fetch a list of all GitHub releases for a repo

If you'd like to [list all releases for a repository](https://developer.github.com/v3/repos/releases/#list-releases-for-a-repository), set the `fetch_release_index` option to `true`.

This will output an `index.json` file in the `output_directory` that contains a [list of all published GitHub Releases](https://developer.github.com/v3/repos/releases/#list-releases-for-a-repository) for the repo.

For example:

```yaml
- name: Fetch All Release Info
  uses: past-due/fetch-release-info@master
  with:
    github_token: '${{ secrets.GITHUB_TOKEN }}'
    fetch_release_index: true
```

### ⭐️ Customize output data filtering

By default, this action filters certain personal / rapidly-changing information from the output files.

#### `filter_release_keys`
> - Description: A JSON array of strings specifying _keys_ to remove from the `release` object (https://developer.github.com/v3/repos/releases/#get-a-single-release)
> - **Default Value:** `'["author"]'`

#### `filter_asset_keys`
> - Description: A JSON array of strings specifying _keys_ to remove from each `asset` object in the `release.assets` array (https://developer.github.com/v3/repos/releases/#get-a-single-release)
> - **Default Value:** `'["uploader", "download_count"]'`

You can customize these properties to filter whatever keys you want by specifying a JSON array of strings.

To disable filtering, set to either `'[]'` or `false`.

For example:

```yaml
- name: Fetch Latest Release Info, Filter Nothing
  uses: past-due/fetch-release-info@master
  with:
    github_token: '${{ secrets.GITHUB_TOKEN }}'
    filter_release_keys: '[]'
    filter_asset_keys: '[]'
```

## License

- MIT License
