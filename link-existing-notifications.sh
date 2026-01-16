#!/bin/bash
# Link existing notifications to subscribed users

cd "$(dirname "$0")"

sqlite3 sql_app.db << 'EOF'
-- Link all existing notifications to users subscribed to their services
INSERT OR IGNORE INTO users_notifications (user_id, notification_id, is_read)
SELECT DISTINCT us.user_id, n.id, 0
FROM notifications n
JOIN users_services us ON n.service_id = us.service_id
WHERE NOT EXISTS (
    SELECT 1 FROM users_notifications un 
    WHERE un.user_id = us.user_id AND un.notification_id = n.id
);

SELECT 'Linked ' || changes() || ' notifications to subscribed users';
EOF

echo "✅ Done! Refresh http://localhost:8000/notifications"
