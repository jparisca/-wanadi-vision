import sqlite3
import sys
import os

# Adjust path to import database modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_utils import clasificar_prompt

db_path = "nexus_prompts.db"

def run_migration():
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Add columns if they don't exist
    cols = [
        ("categoria_id", "INTEGER"),
        ("subcategoria_id", "TEXT"),
        ("votos", "INTEGER DEFAULT 0")
    ]
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(prompts)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    for col, col_type in cols:
        if col not in existing_cols:
            print(f"Adding column {col} to prompts table...")
            cursor.execute(f"ALTER TABLE prompts ADD COLUMN {col} {col_type}")
    conn.commit()
    
    # 2. Update existing prompts with classification
    cursor.execute("SELECT id, canonical_text FROM prompts WHERE categoria_id IS NULL")
    prompts = cursor.fetchall()
    print(f"Found {len(prompts)} prompts to classify.")
    
    for prompt_id, canonical_text in prompts:
        cat_id, sub_slug = clasificar_prompt(canonical_text)
        cursor.execute(
            "UPDATE prompts SET categoria_id = ?, subcategoria_id = ?, votos = COALESCE(votos, 0) WHERE id = ?",
            (cat_id, sub_slug, prompt_id)
        )
    
    # Also default votos = 0 for any NULL votos
    cursor.execute("UPDATE prompts SET votos = 0 WHERE votos IS NULL")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
