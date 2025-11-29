-- Create the 'records' table for the service management database (smtdb)
-- The 'hostname' is set as the PRIMARY KEY to ensure only one entry per host,
-- allowing new entries to automatically update the host's status.
CREATE TABLE IF NOT EXISTS records (
                                       hostname TEXT PRIMARY KEY NOT NULL,
                                       datetime TEXT NOT NULL,
                                       status TEXT NOT NULL, -- running, error, finished
                                       service TEXT NOT NULL, -- system_update, system_highstate
                                       comment TEXT
);