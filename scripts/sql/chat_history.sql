BEGIN;
SET LOCAL lock_timeout = '5s';
CREATE TABLE IF NOT EXISTS public.chat_conversations (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  session_id varchar(200) NOT NULL,
  title varchar(80) NOT NULL,
  checkpoint jsonb,
  lease_token uuid,
  busy_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, session_id)
);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_user_updated ON public.chat_conversations(user_id, updated_at DESC, id);
CREATE TABLE IF NOT EXISTS public.chat_turns (
  id uuid PRIMARY KEY,
  conversation_id uuid NOT NULL REFERENCES public.chat_conversations(id) ON DELETE CASCADE,
  request_id uuid NOT NULL,
  user_text text NOT NULL CHECK (length(user_text) BETWEEN 1 AND 5000),
  assistant_text text,
  result jsonb,
  status varchar(16) NOT NULL CHECK (status IN ('processing','completed','failed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (conversation_id, request_id)
);
CREATE INDEX IF NOT EXISTS ix_chat_turns_conversation_created ON public.chat_turns(conversation_id, created_at DESC, id);
ALTER TABLE public.chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_turns ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.chat_conversations, public.chat_turns FROM anon, authenticated;
NOTIFY pgrst, 'reload schema';
COMMIT;
