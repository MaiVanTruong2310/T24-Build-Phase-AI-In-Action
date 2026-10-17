"""Deploy verified accounts to Supabase Auth and application database."""
import json
import uuid
import psycopg

DATABASE_URL = (
    "postgresql://postgres.uxtpazhbzpoohlhncwbh:1234567890%401234567890AI"
    "@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
)

ACCOUNTS = [
    {
        "email": "admin@vcare.vn",
        "password": "Admin@123456",
        "full_name": "Quản trị viên hệ thống",
        "role": "staff",
        "is_admin": True,
        "qualification": "Quản trị viên trưởng",
    },
    {
        "email": "coordinator@vcare.vn",
        "password": "Coordinator@123456",
        "full_name": "Điều phối viên lâm sàng",
        "role": "staff",
        "is_admin": False,
        "qualification": "Điều phối viên ca trực",
    },
    {
        "email": "patient@vcare.vn",
        "password": "Patient@123456",
        "full_name": "Nguyễn Văn Bệnh Nhân",
        "role": "patient",
        "is_admin": False,
        "qualification": None,
    },
]


def deploy():
    print("Connecting to Supabase PostgreSQL...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Clean up temporary test_staff if any
            cur.execute("""
                DELETE FROM public.coordinator_members WHERE user_id IN (SELECT id FROM public.users WHERE email = 'test_staff@vcare.vn');
                DELETE FROM public.users WHERE email = 'test_staff@vcare.vn';
                DELETE FROM auth.identities WHERE user_id IN (SELECT id FROM auth.users WHERE email = 'test_staff@vcare.vn');
                DELETE FROM auth.users WHERE email = 'test_staff@vcare.vn';
            """)

            for acc in ACCOUNTS:
                email = acc["email"]
                password = acc["password"]
                full_name = acc["full_name"]
                role = acc["role"]
                is_admin = acc["is_admin"]
                qualification = acc["qualification"]

                # Check if user already exists in auth.users
                cur.execute("SELECT id FROM auth.users WHERE email = %s;", (email,))
                row = cur.fetchone()

                if row:
                    auth_id = row[0]
                    print(f"Updating existing user in auth.users: {email} ({auth_id})")
                    cur.execute("""
                        UPDATE auth.users
                        SET encrypted_password = crypt(%s, gen_salt('bf', 10)),
                            email_confirmed_at = COALESCE(email_confirmed_at, now()),
                            email_change = '',
                            phone_change = '',
                            raw_user_meta_data = jsonb_build_object('sub', id::text, 'email', %s::text, 'full_name', %s::text, 'email_verified', true, 'phone_verified', false),
                            updated_at = now()
                        WHERE id = %s;
                    """, (password, email, full_name, auth_id))
                else:
                    auth_id = uuid.uuid4()
                    print(f"Creating user in auth.users: {email} ({auth_id})")
                    cur.execute("""
                        INSERT INTO auth.users (
                            id, instance_id, aud, role, email, encrypted_password,
                            email_confirmed_at, email_change, phone_change,
                            raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
                            confirmation_token, recovery_token, email_change_token_new
                        ) VALUES (
                            %s, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
                            %s, crypt(%s, gen_salt('bf', 10)),
                            now(), '', '',
                            '{"provider":"email","providers":["email"]}'::jsonb,
                            jsonb_build_object('sub', %s::text, 'email', %s::text, 'full_name', %s::text, 'email_verified', true, 'phone_verified', false),
                            now(), now(), '', '', ''
                        );
                    """, (auth_id, email, password, auth_id, email, full_name))

                # Ensure identity in auth.identities
                cur.execute("SELECT id FROM auth.identities WHERE user_id = %s;", (auth_id,))
                if not cur.fetchone():
                    identity_id = uuid.uuid4()
                    cur.execute("""
                        INSERT INTO auth.identities (
                            id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
                        ) VALUES (
                            %s, %s,
                            jsonb_build_object('sub', %s::text, 'email', %s::text, 'full_name', %s::text, 'email_verified', true, 'phone_verified', false),
                            'email', %s::text, now(), now(), now()
                        );
                    """, (identity_id, auth_id, auth_id, email, full_name, auth_id))

                # Ensure record in public.users
                cur.execute("SELECT id FROM public.users WHERE auth_user_id = %s OR email = %s;", (auth_id, email))
                user_row = cur.fetchone()
                if user_row:
                    app_user_id = user_row[0]
                    cur.execute("""
                        UPDATE public.users
                        SET auth_user_id = %s, full_name = %s, role = %s, status = 'active', verified_at = COALESCE(verified_at, now())
                        WHERE id = %s;
                    """, (auth_id, full_name, role, app_user_id))
                else:
                    app_user_id = uuid.uuid4()
                    cur.execute("""
                        INSERT INTO public.users (
                            id, auth_user_id, email, full_name, role, status, verified_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, 'active', now()
                        );
                    """, (app_user_id, auth_id, email, full_name, role))

                # Ensure coordinator_members if staff
                if role == "staff":
                    cur.execute("""
                        INSERT INTO public.coordinator_members (
                            user_id, enabled, is_admin, on_duty, facility_ids, clinical_qualification
                        ) VALUES (
                            %s, true, %s, true, '[]'::jsonb, %s
                        )
                        ON CONFLICT (user_id) DO UPDATE SET
                            enabled = true,
                            is_admin = EXCLUDED.is_admin,
                            on_duty = true,
                            clinical_qualification = EXCLUDED.clinical_qualification;
                    """, (app_user_id, is_admin, qualification))

                print(f"  [OK] Deployed {email} (role: {role}, is_admin: {is_admin})")

        conn.commit()
    print("All accounts successfully deployed to Supabase!")


if __name__ == "__main__":
    deploy()
