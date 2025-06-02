from supabase import create_client
import os
from dotenv import load_dotenv

# .env 파일을 불러와서 환경변수 등록
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabase 클라이언트 생성
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)




if __name__ == "__main__":
    print("✅ Supabase 연결 테스트 시작")
    print("URL:", SUPABASE_URL)
    print("KEY 앞부분:", SUPABASE_KEY[:10])

    try:
        res = supabase.table("i_entry").select("*").limit(1).execute()
        print("데이터 조회 성공 ✅", res.data)
    except Exception as e:
        print("❌ 에러 발생:", e)
