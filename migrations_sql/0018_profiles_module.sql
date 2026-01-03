-- 0018_profiles_module.sql
-- Rename the legacy CV module to Profiles and carry over user grants.

-- Add Profiles module if it doesn't already exist, copying flags from the old CV row when present.
INSERT INTO rb_module (module_key, name, description, is_enabled, created_at, updated_at)
SELECT
    'profiles',
    'Profiles',
    'Profiles (formerly CV)',
    m.is_enabled,
    m.created_at,
    m.updated_at
FROM rb_module m
WHERE m.module_key = 'cv'
  AND NOT EXISTS (SELECT 1 FROM rb_module WHERE module_key = 'profiles');

-- Copy per-user grants from the old CV module.
INSERT INTO rb_user_module (user_id, module_key, has_access, granted_by, granted_at)
SELECT
    um.user_id,
    'profiles',
    um.has_access,
    um.granted_by,
    um.granted_at
FROM rb_user_module um
WHERE um.module_key = 'cv'
  AND NOT EXISTS (
    SELECT 1 FROM rb_user_module x
    WHERE x.user_id = um.user_id
      AND x.module_key = 'profiles'
  );

-- Remove the legacy CV grants and module row now that copies exist.
DELETE FROM rb_user_module WHERE module_key = 'cv';
DELETE FROM rb_module WHERE module_key = 'cv';
