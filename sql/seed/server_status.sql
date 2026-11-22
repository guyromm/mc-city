INSERT INTO minecraft.server_status(id) VALUES (true) ON CONFLICT DO NOTHING;   -- singleton row the status worker updates
