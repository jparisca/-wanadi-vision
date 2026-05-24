from refinery.cleaner import PromptRefinery
from database.db_utils import save_prompt_to_db

if __name__ == "__main__":
    refinery = PromptRefinery()

    # Simulación de un post real de X
    post_ejemplo = (
        "My latest flux generation! A melancholic 90s analog photography, grain, soft flash, "
        "empty parking lot at night, kodak portra tones --ar 4:3 --v 6 --stylize 300 "
        "https://x.com/fakeurl"
    )

    resultado = refinery.process(post_ejemplo)

    print("\n🧪 RESULTADO DEL REFINERY:")
    print(f"  Clean text: {resultado['clean_text'][:80]}...")
    print(f"  Engine: {resultado['engine']}")
    print(f"  Params: {resultado['parameters']}")

    # Guardar en BD
    save_prompt_to_db(
        refinery_result=resultado,
        platform="X",
        url="https://x.com/example/status/123456",
        author="@ai_artist",
        engagement_score=124.5  # likes + retweets simulados
    )
