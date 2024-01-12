import asyncio
import os
import random
import re
import logging

import httpx
from fake_useragent import UserAgent

logger = logging.getLogger("BingImageCreator")
ua = UserAgent(browsers=["edge"])

BING_URL = os.getenv("BING_URL", "https://www.bing.com")
# Generate random IP between range 13.104.0.0/14
FORWARDED_IP = (
    f"13.{random.randint(104, 107)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
)
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "referrer": "https://www.bing.com/images/create/",
    "origin": "https://www.bing.com",
    "user-agent": ua.random,
    "x-forwarded-for": FORWARDED_IP,
}


class GenerateImageException(Exception):
    """
    Exception raised when image generation fails
    """


class GenerateImagePromptException(GenerateImageException):
    """
    Exception raised when prompt is blocked by Bing
    """


class ImageGen:
    """
    Image generation by Microsoft Bing
    """

    def __init__(
        self,
        auth_cookie: str | None = None,
        all_cookies: list[dict[str, str]] | None = None,
        proxy: str | None = None,
    ) -> None:
        if auth_cookie is None and not all_cookies:
            raise RuntimeError("No auth cookie provided")
        self.session = httpx.AsyncClient(
            base_url=BING_URL,
            headers={**HEADERS, "user-agent": ua.random},
            trust_env=True,
            proxy=proxy,
        )
        if auth_cookie:
            self.session.cookies.update({"_U": auth_cookie})
        if all_cookies:
            for cookie in all_cookies:
                self.session.cookies.update({cookie["name"]: cookie["value"]})

    async def __aenter__(self):
        await self.session.__aenter__()
        return self

    async def __aexit__(self, *excinfo):
        await self.session.__aexit__(*excinfo)

    async def get_images(self, prompt: str) -> list[str]:
        """
        Fetches image links from Bing
        """
        # https://www.bing.com/images/create?q=<PROMPT>&rt=3&FORM=GENCRE
        response = await self.session.post(
            "/images/create",
            params={"q": prompt, "rt": "3", "FORM": "GENCRE"},
            data={"q": prompt, "qs": "ds"},
            follow_redirects=False,
        )
        content = response.text
        if "this prompt has been blocked" in content.lower():
            raise GenerateImagePromptException(
                "Your prompt has been blocked by Bing. Try to change any bad words and try again.",
            )
        if not response.is_redirect:
            # if rt4 fails, try rt3
            response = await self.session.post(
                "/images/create",
                params={"q": prompt, "rt": "4", "FORM": "GENCRE"},
                follow_redirects=False,
                timeout=200,
            )
            if not response.is_redirect:
                logger.error(
                    f"Need redirect response but got, {response.status_code} {response.text}"
                )
                raise GenerateImageException("Redirect failed")
        # Get redirect URL
        redirect_url = response.headers["Location"].replace("&nfy=1", "")
        request_id = redirect_url.split("id=")[-1]
        await self.session.get(redirect_url)
        # Poll for results
        while True:
            # https://www.bing.com/images/create/async/results/{ID}?q={PROMPT}
            response = await self.session.get(
                f"/images/create/async/results/{request_id}",
                params={"q": prompt},
                timeout=600,
            )
            if response.status_code != 200:
                raise GenerateImageException("Could not get results")
            content = response.text
            if content and content.find("errorMessage") == -1:
                break

            await asyncio.sleep(1)
            continue
        # Use regex to search for src=""
        image_links = re.findall(r'src="([^"]+)"', content)
        # Remove size limit
        normal_image_links = [link.split("?w=")[0] for link in image_links]
        # Remove duplicates
        normal_image_links = list(set(normal_image_links))

        # Bad images
        bad_images = [
            "https://r.bing.com/rp/in-2zU3AJUdkgFe7ZKv19yPBHVs.png",
            "https://r.bing.com/rp/TX9QuO3WzcCJz1uaaSwQAz39Kb0.jpg",
        ]
        for im in normal_image_links:
            if im in bad_images:
                raise GenerateImageException("Bad images")
        # No images
        if not normal_image_links:
            raise GenerateImageException("No images")
        normal_image_links = [i for i in normal_image_links if not i.endswith(".svg")]
        return normal_image_links

    async def download_image(self, link: str) -> bytes:
        try:
            response = await self.session.get(link)
        except httpx.InvalidURL as url_exception:
            raise GenerateImageException(
                "Inappropriate contents found in the generated images. Please try again or try another prompt.",
            ) from url_exception
        else:
            response.raise_for_status()
            return response.content
