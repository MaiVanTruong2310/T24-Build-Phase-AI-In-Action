-- ==============================================================================
-- SCRIPT TẠO / CẬP NHẬT TÀI KHOẢN ADMIN TRÊN SUPABASE (P-124)
-- Chạy trực tiếp trên Supabase Studio -> SQL Editor
-- ==============================================================================

DO $$
DECLARE
    -- 1. ĐIỀN THÔNG TIN TÀI KHOẢN ADMIN Ở ĐÂY:
    target_email TEXT := 'admin@vcare.vn';
    target_password TEXT := 'Admin@123456';
    target_full_name TEXT := 'Quản trị viên hệ thống';
    
    target_auth_id UUID;
    target_user_id UUID;
BEGIN
    -- Đảm bảo extension pgcrypto đã sẵn sàng để hash password bcrypt
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    -- Kiểm tra xem email đã tồn tại trong auth.users chưa
    SELECT id INTO target_auth_id FROM auth.users WHERE email = target_email;

    IF target_auth_id IS NOT NULL THEN
        -- Cập nhật mật khẩu và metadata cho tài khoản đã có
        UPDATE auth.users
        SET encrypted_password = crypt(target_password, gen_salt('bf', 10)),
            email_confirmed_at = COALESCE(email_confirmed_at, now()),
            raw_user_meta_data = jsonb_build_object(
                'sub', target_auth_id::text,
                'email', target_email,
                'full_name', target_full_name,
                'email_verified', true,
                'phone_verified', false
            ),
            updated_at = now()
        WHERE id = target_auth_id;
        
        RAISE NOTICE 'Đã cập nhật auth.users cho % (id: %)', target_email, target_auth_id;
    ELSE
        -- Tạo mới user trong auth.users
        target_auth_id := gen_random_uuid();
        INSERT INTO auth.users (
            id,
            instance_id,
            aud,
            role,
            email,
            encrypted_password,
            email_confirmed_at,
            raw_app_meta_data,
            raw_user_meta_data,
            created_at,
            updated_at,
            confirmation_token,
            recovery_token,
            email_change_token_new
        ) VALUES (
            target_auth_id,
            '00000000-0000-0000-0000-000000000000',
            'authenticated',
            'authenticated',
            target_email,
            crypt(target_password, gen_salt('bf', 10)),
            now(),
            '{"provider":"email","providers":["email"]}'::jsonb,
            jsonb_build_object(
                'sub', target_auth_id::text,
                'email', target_email,
                'full_name', target_full_name,
                'email_verified', true,
                'phone_verified', false
            ),
            now(),
            now(),
            '',
            '',
            ''
        );
        RAISE NOTICE 'Đã tạo mới auth.users cho % (id: %)', target_email, target_auth_id;
    END IF;

    -- Đảm bảo bản ghi trong auth.identities
    IF NOT EXISTS (SELECT 1 FROM auth.identities WHERE user_id = target_auth_id) THEN
        INSERT INTO auth.identities (
            id,
            user_id,
            identity_data,
            provider,
            provider_id,
            last_sign_in_at,
            created_at,
            updated_at
        ) VALUES (
            gen_random_uuid(),
            target_auth_id,
            jsonb_build_object(
                'sub', target_auth_id::text,
                'email', target_email,
                'full_name', target_full_name,
                'email_verified', true,
                'phone_verified', false
            ),
            'email',
            target_auth_id::text,
            now(),
            now(),
            now()
        );
    END IF;

    -- Đảm bảo bản ghi hồ sơ ứng dụng trong public.users
    SELECT id INTO target_user_id FROM public.users WHERE auth_user_id = target_auth_id OR email = target_email;

    IF target_user_id IS NOT NULL THEN
        UPDATE public.users
        SET auth_user_id = target_auth_id,
            full_name = target_full_name,
            role = 'staff',
            status = 'active',
            updated_at = now()
        WHERE id = target_user_id;
    ELSE
        target_user_id := gen_random_uuid();
        INSERT INTO public.users (
            id,
            auth_user_id,
            email,
            full_name,
            role,
            status,
            created_at,
            updated_at
        ) VALUES (
            target_user_id,
            target_auth_id,
            target_email,
            target_full_name,
            'staff',
            'active',
            now(),
            now()
        );
    END IF;

    -- Phân quyền Admin vào bảng public.coordinator_members
    INSERT INTO public.coordinator_members (
        user_id,
        enabled,
        is_admin,
        on_duty,
        facility_ids,
        clinical_qualification
    ) VALUES (
        target_user_id,
        true,
        true,
        true,
        '[]'::jsonb,
        'Quản trị viên trưởng'
    )
    ON CONFLICT (user_id) DO UPDATE SET
        enabled = true,
        is_admin = true,
        on_duty = true,
        facility_ids = '[]'::jsonb,
        clinical_qualification = 'Quản trị viên trưởng';

    RAISE NOTICE 'Hoàn tất! Tài khoản % đã có quyền Admin.', target_email;
END $$;
