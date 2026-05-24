from fastapi import APIRouter, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from refinery.cleaner import PromptRefinery
from database.db_utils import save_prompt_to_db
from search.embed_worker import embed_pending_prompts
from search.index_manager import IndexManager

router = APIRouter()
refinery = PromptRefinery()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Admin | Add Prompt</title>
    <style>
        :root {
            --bg: #0a0a0f;
            --surface: #13131a;
            --primary: #00ffcc;
            --text: #e0e0e0;
            --border: #2a2a35;
        }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            background-color: var(--surface);
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            width: 100%;
            max-width: 500px;
            box-shadow: 0 8px 32px rgba(0, 255, 204, 0.1);
        }
        h2 {
            margin-top: 0;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 1.2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }
        .form-group {
            margin-bottom: 1.2rem;
        }
        label {
            display: block;
            margin-bottom: 0.4rem;
            font-size: 0.9rem;
            color: #888;
        }
        input, select, textarea {
            width: 100%;
            background-color: #1a1a24;
            border: 1px solid var(--border);
            color: white;
            padding: 0.8rem;
            border-radius: 6px;
            font-family: inherit;
            box-sizing: border-box;
            outline: none;
            transition: border-color 0.2s;
        }
        input:focus, select:focus, textarea:focus {
            border-color: var(--primary);
        }
        textarea {
            resize: vertical;
            min-height: 120px;
        }
        button {
            width: 100%;
            background-color: var(--primary);
            color: #000;
            border: none;
            padding: 0.8rem;
            font-weight: bold;
            border-radius: 6px;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: opacity 0.2s;
        }
        button:hover {
            opacity: 0.9;
        }
        .status {
            margin-top: 1rem;
            padding: 0.8rem;
            border-radius: 6px;
            font-size: 0.9rem;
            display: none;
        }
        .status.success {
            display: block;
            background-color: rgba(0, 255, 204, 0.1);
            color: var(--primary);
            border: 1px solid var(--primary);
        }
        .status.error {
            display: block;
            background-color: rgba(255, 50, 50, 0.1);
            color: #ff4444;
            border: 1px solid #ff4444;
        }
    </style>
</head>
<body>

<div class="container">
    <h2>Nexus Core | Manual Ingestion</h2>
    
    <div id="statusMessage" class="status {status_class}">
        {message}
    </div>

    <form method="POST" action="/api/v1/admin/add-prompt">
        <div class="form-group">
            <label>Prompt Text</label>
            <textarea name="prompt_text" required placeholder="A beautiful cyberpunk city at night..."></textarea>
        </div>
        
        <div class="form-group">
            <label>Platform Source</label>
            <input type="text" name="platform" value="manual" required>
        </div>
        
        <div class="form-group">
            <label>AI Engine</label>
            <select name="engine">
                <option value="midjourney">Midjourney</option>
                <option value="stable_diffusion">Stable Diffusion</option>
                <option value="flux">Flux</option>
                <option value="dall_e">DALL-E</option>
                <option value="chatgpt">ChatGPT</option>
                <option value="gemini">Gemini</option>
                <option value="unknown">Unknown</option>
            </select>
        </div>

        <div class="form-group">
            <label>Author</label>
            <input type="text" name="author" value="admin">
        </div>

        <button type="submit">Inject to Vector DB</button>
    </form>
</div>

</body>
</html>
"""

def update_vector_db():
    print("[Admin] Computando embeddings para el nuevo prompt...")
    embed_pending_prompts()
    print("[Admin] Refrescando índice FAISS...")
    manager = IndexManager()
    manager.refresh()

@router.get("/add-prompt", response_class=HTMLResponse)
async def get_add_prompt_form(request: Request, msg: str = "", status: str = ""):
    return HTML_TEMPLATE.replace("{message}", msg).replace("{status_class}", status)

@router.post("/add-prompt", response_class=HTMLResponse)
async def process_add_prompt(
    background_tasks: BackgroundTasks,
    prompt_text: str = Form(...),
    platform: str = Form("manual"),
    engine: str = Form("unknown"),
    author: str = Form("admin")
):
    try:
        # Refinar texto
        refined = refinery.process(prompt_text)
        
        # Guardar en SQLite
        save_prompt_to_db(
            refinery_result=refined,
            platform=platform,
            url=f"manual://{author}",
            author=author,
            engagement_score=100.0  # Los manuales tienen alta prioridad
        )
        
        # Lanzar actualización de FAISS en background para no bloquear la respuesta UI
        background_tasks.add_task(update_vector_db)
        
        msg = "Prompt Ingested! Embedding and indexing in background..."
        return HTML_TEMPLATE.replace("{message}", msg).replace("{status_class}", "success")
    except Exception as e:
        return HTML_TEMPLATE.replace("{message}", f"Error: {str(e)}").replace("{status_class}", "error")
