import httpx
import base64


async def get_repository(owner: str, repo: str):
    url = f"https://api.github.com/repos/{owner}/{repo}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        data = response.json()

        raise Exception(
            f"GitHub API error: {data.get('message', 'Unknown error')}"
        )

    return response.json()


async def get_repository_tree(owner: str, repo: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD"
    params = {"recursive": "1"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        data = response.json()

        raise Exception(
            f"GitHub API error: {data.get('message', 'Unknown error')}"
        )

    return response.json()

async def get_file_content(owner: str, repo: str, path: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        data = response.json()
        raise Exception(
            f"GitHub API error: {data.get('message', 'Unknown error')}"
        )

    data = response.json()

    if data.get("encoding") == "base64":
        content = base64.b64decode(data["content"]).decode("utf-8")

        return content

    return data.get("content", "")