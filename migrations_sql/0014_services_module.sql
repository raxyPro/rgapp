-- 0014_services_module.sql
-- Register the Services module and grant access to existing users.
-- Safe to run multiple times.

INSERT INTO rb_module (module_key, name, description, is_enabled)
SELECT 'services', 'Services', 'Browse vCard skills/services and start chats', 1
WHERE NOT EXISTS (SELECT 1 FROM rb_module WHERE module_key = 'services');

INSERT INTO rb_user_module (user_id, module_key, has_access)
SELECT u.user_id, 'services', 1
FROM rb_user u
WHERE u.status <> 'deleted'
  AND NOT EXISTS (
    SELECT 1 FROM rb_user_module um
    WHERE um.user_id = u.user_id AND um.module_key = 'services'
  );
