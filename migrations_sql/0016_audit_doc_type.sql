-- Add doc_type to audit entries (used for vCard create/update history).
ALTER TABLE rb_audit
  ADD COLUMN doc_type varchar(20) DEFAULT NULL AFTER row_id;
