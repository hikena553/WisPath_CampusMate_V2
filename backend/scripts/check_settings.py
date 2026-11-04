import sys
sys.path.insert(0, '.')
from app.core.database import SessionLocal
from app.models.setting import SystemSetting
db = SessionLocal()
for k in ('llm_api_key', 'dashscope_api_key', 'llm_tts_voice', 'llm_tts_prompt'):
    row = db.query(SystemSetting).filter(SystemSetting.key == k).first()
    if row:
        v = (row.value or '').strip()
        head = v[:40] if v else ''
        tail = '...' if v and len(v) > 40 else ''
        print(f'{k}=({len(v) if v else 0} chars) {head}{tail}')
    else:
        print(f'{k}=<not set>')
db.close()
