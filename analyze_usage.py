import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env from backend/.env
load_dotenv("backend/.env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Add SSL requirement
if "sslmode" not in DATABASE_URL:
    separator = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL += f"{separator}sslmode=require"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("✅ Database Connected Successfully!\n")
        
        # ============================
        # 1. TOTAL USERS
        # ============================
        total_users = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        verified_users = conn.execute(text("SELECT COUNT(*) FROM users WHERE is_verified = true")).scalar()
        print(f"📊 Total Users: {total_users}")
        print(f"   Verified Users: {verified_users}")
        
        # ============================
        # 2. PDF GENERATIONS - Last 30 Days
        # ============================
        print("\n--- PDF Generations (Last 30 Days) ---")
        result_pdf = conn.execute(text("""
            SELECT DATE(created_at) as day, COUNT(*) as count 
            FROM pdf_generations 
            WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at) 
            ORDER BY day DESC;
        """)).fetchall()
        
        total_pdf_30d = 0
        for row in result_pdf:
            print(f"  {row[0]}: {row[1]} PDFs")
            total_pdf_30d += row[1]
        
        days_with_data = len(result_pdf)
        avg_pdf = total_pdf_30d / max(days_with_data, 1)
        print(f"\n  Total (30d): {total_pdf_30d}")
        print(f"  Days Active: {days_with_data}")
        print(f"  Avg PDF/Day: {avg_pdf:.1f}")

        # ============================
        # 3. TEST PORTAL - Last 30 Days
        # ============================
        print("\n--- Test Portal Activity (Last 30 Days) ---")
        result_test = conn.execute(text("""
            SELECT DATE(created_at) as day, COUNT(*) as count 
            FROM test_attempts 
            WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at) 
            ORDER BY day DESC;
        """)).fetchall()
        
        total_tests_30d = 0
        for row in result_test:
            print(f"  {row[0]}: {row[1]} tests")
            total_tests_30d += row[1]
        
        avg_tests = total_tests_30d / max(len(result_test), 1)
        print(f"\n  Total Tests (30d): {total_tests_30d}")
        print(f"  Avg Tests/Day: {avg_tests:.1f}")

        # ============================
        # 4. DAILY ACTIVE USERS (DAU) - Last 30 Days
        # ============================
        print("\n--- Daily Active Users (Last 30 Days) ---")
        result_dau = conn.execute(text("""
            SELECT DATE(activity_time) as day, COUNT(DISTINCT user_id) as active_users
            FROM (
                SELECT created_at as activity_time, user_id FROM pdf_generations
                UNION ALL
                SELECT created_at as activity_time, user_id FROM test_attempts
            ) as activities
            WHERE activity_time > NOW() - INTERVAL '30 days'
            GROUP BY DATE(activity_time)
            ORDER BY day DESC;
        """)).fetchall()
        
        for row in result_dau:
            print(f"  {row[0]}: {row[1]} users")
        
        avg_dau = sum([r[1] for r in result_dau]) / max(len(result_dau), 1)
        print(f"\n  Avg DAU: {avg_dau:.1f}")

        # ============================
        # 5. TOP USERS BY GENERATION COUNT (Last 30 Days)
        # ============================
        print("\n--- Top 10 Users by PDF Generation (Last 30 Days) ---")
        result_top = conn.execute(text("""
            SELECT u.email, u.name, COUNT(p.id) as gen_count
            FROM pdf_generations p
            JOIN users u ON p.user_id = u.id
            WHERE p.created_at > NOW() - INTERVAL '30 days'
            GROUP BY u.email, u.name
            ORDER BY gen_count DESC
            LIMIT 10;
        """)).fetchall()
        
        for i, row in enumerate(result_top, 1):
            print(f"  {i}. {row[1] or 'N/A'} ({row[0]}): {row[2]} PDFs")

        # ============================
        # 6. INSTITUTE GENERATIONS - Last 30 Days
        # ============================
        print("\n--- Institute Generations (Last 30 Days) ---")
        result_inst = conn.execute(text("""
            SELECT DATE(created_at) as day, COUNT(*) as count 
            FROM institute_generations 
            WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at) 
            ORDER BY day DESC;
        """)).fetchall()
        
        total_inst = sum([r[1] for r in result_inst])
        for row in result_inst:
            print(f"  {row[0]}: {row[1]} generations")
        print(f"\n  Total Institute Generations (30d): {total_inst}")

        # ============================
        # SUMMARY
        # ============================
        print("\n" + "="*50)
        print("📊 SUMMARY")
        print("="*50)
        print(f"  Total Users: {total_users} ({verified_users} verified)")
        print(f"  Avg PDFs/Day: {avg_pdf:.1f}")
        print(f"  Avg Tests/Day: {avg_tests:.1f}")
        print(f"  Avg DAU: {avg_dau:.1f}")
        print(f"  Total API Calls/Day (est): ~{avg_pdf * 10 + avg_tests * 12:.0f}")
        print("="*50)
        
except Exception as e:
    print(f"❌ Database error: {e}")
    import traceback
    traceback.print_exc()
