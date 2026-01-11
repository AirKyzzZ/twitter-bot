"""Twitter API v2 client."""

from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from twitter_bot.exceptions import TwitterAPIError


@dataclass
class Tweet:
    """Posted tweet data."""

    id: str
    text: str


class TwitterClient:
    """Client for Twitter API v2."""

    BASE_URL = "https://api.twitter.com/2"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_secret: str,
        bearer_token: str = "",
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_secret = access_secret
        self.bearer_token = bearer_token

        # For OAuth 1.0a we need to use httpx with auth
        # For simplicity, using OAuth 2.0 Bearer token for read operations
        # and OAuth 1.0a User Context for write operations
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "TwitterClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _get_oauth1_header(self, method: str, url: str) -> dict[str, str]:
        """Generate OAuth 1.0a authorization header.

        This is a simplified implementation. For production, use requests-oauthlib
        or authlib for proper OAuth 1.0a signing.
        """
        # For now, we'll use a placeholder that requires the user to set up
        # proper OAuth. In production, you'd use requests_oauthlib.OAuth1
        import base64
        import hashlib
        import hmac
        import secrets
        import time
        import urllib.parse

        oauth_nonce = secrets.token_hex(16)
        oauth_timestamp = str(int(time.time()))

        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_nonce": oauth_nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": oauth_timestamp,
            "oauth_token": self.access_token,
            "oauth_version": "1.0",
        }

        # Create signature base string
        param_string = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
            for k, v in sorted(oauth_params.items())
        )

        signature_base = "&".join([
            method.upper(),
            urllib.parse.quote(url, safe=""),
            urllib.parse.quote(param_string, safe=""),
        ])

        # Create signing key
        signing_key = "&".join([
            urllib.parse.quote(self.api_secret, safe=""),
            urllib.parse.quote(self.access_secret, safe=""),
        ])

        # Generate signature
        signature = base64.b64encode(
            hmac.new(
                signing_key.encode(),
                signature_base.encode(),
                hashlib.sha1,
            ).digest()
        ).decode()

        oauth_params["oauth_signature"] = signature

        # Build Authorization header
        auth_header = "OAuth " + ", ".join(
            f'{k}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        )

        return {"Authorization": auth_header}

    def upload_media(self, file_path: str) -> str:
        """Upload media to Twitter (v1.1 API).

        Args:
            file_path: Path to the image file

        Returns:
            Media ID string

        Raises:
            TwitterAPIError: If upload fails
        """
        url = "https://upload.twitter.com/1.1/media/upload.json"
        headers = self._get_oauth1_header("POST", url)

        # httpx handles multipart boundary automatically if we don't set Content-Type
        if "Content-Type" in headers:
            del headers["Content-Type"]

        try:
            with open(file_path, "rb") as f:
                files = {"media": f}
                response = self._client.post(url, headers=headers, files=files)
            
            if response.status_code != 200:
                raise TwitterAPIError(
                    f"Media upload failed: {response.text}",
                    status_code=response.status_code
                )
                
            return response.json()["media_id_string"]
        except Exception as e:
            if isinstance(e, TwitterAPIError):
                raise
            raise TwitterAPIError(f"Media upload failed: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def post_tweet(self, text: str, media_ids: list[str] | None = None) -> Tweet:
        """Post a tweet.

        Args:
            text: Tweet text (max 280 characters)
            media_ids: Optional list of media IDs to attach

        Returns:
            Tweet object with id and text

        Raises:
            TwitterAPIError: If posting fails
        """
        if len(text) > 280:
            raise TwitterAPIError("Tweet exceeds 280 characters")

        url = f"{self.BASE_URL}/tweets"
        headers = self._get_oauth1_header("POST", url)
        headers["Content-Type"] = "application/json"

        payload = {"text": text}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}

        try:
            response = self._client.post(
                url,
                headers=headers,
                json=payload,
            )
        except httpx.HTTPError as e:
            raise TwitterAPIError(f"HTTP error posting tweet: {e}") from e

        if response.status_code == 429:
            raise TwitterAPIError("Rate limit exceeded", status_code=429)

        if response.status_code == 403:
            raise TwitterAPIError("Forbidden - check API permissions", status_code=403)

        if response.status_code != 201:
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", response.text)
            except Exception:
                error_msg = response.text
            raise TwitterAPIError(
                f"Failed to post tweet: {error_msg}",
                status_code=response.status_code,
            )

        try:
            data = response.json()
            tweet_data = data.get("data", {})
            return Tweet(
                id=tweet_data.get("id", ""),
                text=tweet_data.get("text", text),
            )
        except Exception as e:
            raise TwitterAPIError(f"Failed to parse response: {e}") from e

    def verify_credentials(self) -> bool:
        """Verify that credentials are valid.

        Returns:
            True if credentials are valid
        """
        url = f"{self.BASE_URL}/users/me"
        headers = self._get_oauth1_header("GET", url)

        try:
            response = self._client.get(url, headers=headers)
            return response.status_code == 200
        except Exception:
            return False
