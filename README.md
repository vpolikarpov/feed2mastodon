# feed2mastodon

This is a simple script that reads an RSS feed and posts entries to a Mastodon account.

## Usage

```shell
python feed2mastodon.py [-h|--help]
    [--state-file STATE_FILE]
    [--max-posts MAX_POSTS]
    [--post-template POST_TEMPLATE]
    [--post-hashtags POST_HASHTAGS]
    [--post-max-length POST_MAX_LENGTH]
    [--post-max-images POST_MAX_IMAGES]
    [--post-visibility {public,unlisted,private,direct}]
    [--mastodon-api-base-url MASTODON_API_BASE_URL]
    [--dry-run] [-v|--verbose]
    feed_url

positional arguments:
  feed_url              URL of the feed to fetch

options:
  -h, --help            show this help message and exit
  --state-file STATE_FILE
                        file to store state
  --max-posts MAX_POSTS
                        maximum number of posts to push
  --post-template POST_TEMPLATE
                        Template of the post
  --post-hashtags POST_HASHTAGS
                        Hashtags to add to the post
  --post-max-length POST_MAX_LENGTH
                        Maximum length of the post
  --post-max-images POST_MAX_IMAGES
                        Maximum number of images to attach to the post
  --post-visibility {public,unlisted,private,direct}
                        Visibility of the post in Mastodon
  --mastodon-api-base-url MASTODON_API_BASE_URL
                        Mastodon API base URL
  --dry-run             do not push to Mastodon
  -v, --verbose         increase output verbosity
```

Authentication is controlled by environment variables:

- `MASTODON_CLIENT_ID`
- `MASTODON_CLIENT_SECRET`
- `MASTODON_ACCESS_TOKEN`

Optionally, you can set `MASTODON_API_BASE_URL` that works as a default value for the `--mastodon-api-base-url` option.
