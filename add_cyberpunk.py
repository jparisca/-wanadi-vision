import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from refinery.cleaner import PromptRefinery
from database.db_utils import save_prompt_to_db

refinery = PromptRefinery()

cyberpunk_prompts = [
    "A cinematic shot of a cyberpunk street at night, neon signs reflecting on wet rainy pavement, soft bokeh, Unreal Engine 5 render, high detail --ar 16:9 --v 6.0",
    "Cyberpunk wanderer standing in a dark futuristic alley during heavy rain, dramatic neon lighting, volumetric fog, cinematic style, detailed parameters --ar 21:9 --v 6.0",
    "Rainy cyberpunk cityscape, towering skyscrapers with holograms, flying cars, cinematic composition, mood lighting, masterpiece --ar 16:9 --v 6.0"
]

print("🚀 Insertando prompts de prueba de Cyberpunk...")
for idx, text in enumerate(cyberpunk_prompts, 1):
    refined = refinery.process(text)
    save_prompt_to_db(
        refinery_result=refined,
        platform="X",
        url=f"https://x.com/cyberpunk_test/{idx}",
        author="cyber_creator_99",
        engagement_score=45.5 * idx
    )

print("✅ Prompts insertados con éxito.")
