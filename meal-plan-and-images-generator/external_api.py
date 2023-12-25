import openai


async def openai_get_generated_image_url(prompt: str) -> str:
    response = await openai.Image.acreate(
        prompt=prompt,
        n=1,
        size="1024x1024",
    )
    return response["data"][0]["url"]
