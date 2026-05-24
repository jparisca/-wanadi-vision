import re
import hashlib
import json

class PromptRefinery:
    def __init__(self):
        # Expresión regular para parámetros de Midjourney (ej. --ar 16:9)
        self.mj_param_pattern = re.compile(r'(--[a-zA-Z0-9]+)\s+([a-zA-Z0-9:\.]+)')
        
        # Filtros de palabras inútiles (buzzwords sociales)
        self.noise_words = [
            r'mira lo que generé', r'look at this', r'my latest generation',
            r'qué opinan\?', r'what do you think\?'
        ]
        
        # Mapeo de parámetros para normalización de Midjourney
        self.mj_mapping = {
            "ar": "aspect_ratio",
            "aspect": "aspect_ratio",
            "v": "version",
            "version": "version",
            "s": "stylize",
            "stylize": "stylize",
            "style": "style",
            "c": "chaos",
            "chaos": "chaos",
            "w": "weird",
            "weird": "weird",
            "q": "quality",
            "quality": "quality",
            "niji": "niji"
        }

    def _normalize_text(self, text: str) -> str:
        """
        Aplica la normalización estricta definida para el Hash ID.
        Conserva alfanuméricos, espacios, comas, dos puntos y guiones.
        """
        normalized = text.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        # Remueve todo excepto letras, números, espacios, comas, dos puntos y guiones
        normalized = re.sub(r"[^\w\s,:-]", "", normalized)
        return normalized.strip()

    def process(self, raw_text: str) -> dict:
        """
        Procesa el texto crudo y devuelve el prompt limpio, el motor detectado
        y los parámetros estructurados (raw, normalized, confidence).
        """
        text = raw_text
        
        # 1. Limpiar URLs
        text = re.sub(r'http[s]?://\S+', '', text)
        
        # 2. Detectar Motor de IA inicialmente
        engine = "Unknown"
        confidence = 0.0
        
        # 3. Extraer parámetros según el motor
        raw_params = {}
        normalized_params = {}
        
        # Caso Midjourney
        mj_matches = list(self.mj_param_pattern.finditer(text))
        if mj_matches or "--v" in raw_text or "--ar" in raw_text:
            engine = "Midjourney"
            confidence = 1.0
            for match in mj_matches:
                param_name = match.group(1).strip('-')
                param_value = match.group(2)
                raw_params[f"--{param_name}"] = param_value
                
                # Normalizar parámetro si está en el mapeo
                norm_name = self.mj_mapping.get(param_name)
                if norm_name:
                    normalized_params[norm_name] = param_value
            
            # Remover parámetros de Midjourney del texto
            clean_text = self.mj_param_pattern.sub('', text)
            
        # Caso Stable Diffusion (Automático / WebUI)
        elif "Steps:" in raw_text and "Sampler:" in raw_text:
            engine = "Stable Diffusion"
            confidence = 0.95
            
            # Extraer parámetros de SD usando regex
            sd_patterns = {
                "Steps": r"Steps:\s*(\d+)",
                "Sampler": r"Sampler:\s*([a-zA-Z0-9_\+\s]+)(?:,|$)",
                "CFG scale": r"CFG scale:\s*([0-9\.]+)",
                "Size": r"Size:\s*(\d+x\d+)"
            }
            
            for key, pattern in sd_patterns.items():
                match = re.search(pattern, text)
                if match:
                    val = match.group(1).strip()
                    raw_params[key] = val
                    # Normalización estándar para SD
                    norm_key = key.lower().replace(" ", "_")
                    normalized_params[norm_key] = val
            
            # El clean_text para SD suele ser todo lo que está antes de "Steps:"
            clean_text = text.split("Steps:")[0].strip()
            
        else:
            # Caso genérico / Flux sin metadatos
            clean_text = text
            # Si el texto contiene palabras clave pero no parámetros estructurados
            if "flux" in raw_text.lower():
                engine = "Flux"
                confidence = 0.5 # Detección débil por palabra clave
            elif "dall-e" in raw_text.lower() or "dalle" in raw_text.lower():
                engine = "DALL-E"
                confidence = 0.5

        # 4. Remover frases sociales (ruido)
        for noise in self.noise_words:
            clean_text = re.sub(noise, '', clean_text, flags=re.IGNORECASE)
            
        clean_text = clean_text.strip()
        
        # 5. Normalizar para Hash y generar el SHA-256
        normalized_for_hash = self._normalize_text(clean_text)
        hash_id = hashlib.sha256(normalized_for_hash.encode('utf-8')).hexdigest()
        
        return {
            "hash_id": hash_id,
            "raw_text": raw_text,
            "clean_text": clean_text,
            "engine": engine,
            "parameters": {
                "raw": raw_params,
                "normalized": normalized_params,
                "confidence": confidence
            }
        }

if __name__ == "__main__":
    refinery = PromptRefinery()
    
    # Pruebas
    print("="*50)
    print("🧪 PROBANDO REFINERY CON EL NUEVO FORMATO V1")
    print("="*50)
    
    # Test 1: Midjourney
    mj_post = "Cinematic retro portrait of a cybernetic warrior --ar 16:9 --v 6.0 --style raw"
    res_mj = refinery.process(mj_post)
    print("🚀 MIDJOURNEY:")
    print(f"Clean: {res_mj['clean_text']}")
    print(f"Engine: {res_mj['engine']}")
    print(f"Params: {json.dumps(res_mj['parameters'], indent=2)}")
    print(f"Hash ID: {res_mj['hash_id']}\n")
    
    # Test 2: Stable Diffusion
    sd_post = "cute anime girl, masterpiece, detailed\nSteps: 20, Sampler: Euler a, CFG scale: 7, Seed: 1234, Size: 512x512"
    res_sd = refinery.process(sd_post)
    print("🚀 STABLE DIFFUSION:")
    print(f"Clean: {res_sd['clean_text']}")
    print(f"Engine: {res_sd['engine']}")
    print(f"Params: {json.dumps(res_sd['parameters'], indent=2)}")
    print(f"Hash ID: {res_sd['hash_id']}\n")
