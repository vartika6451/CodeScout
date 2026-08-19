import httpx


async def get_repository(owner: str, repo: str):
    url = f"https://api.github.com/repos/{owner}/{repo}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    response.raise_for_status()

    return response.json()