-- Create database
CREATE DATABASE observer;

-- Create tables
CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(255) PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address VARCHAR(45),
    last_seen TIMESTAMP,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metrics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    timestamp BIGINT NOT NULL,
    cpu_percent FLOAT,
    memory_percent FLOAT,
    disk_percent FLOAT,
    network_in_bytes BIGINT,
    network_out_bytes BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_timestamp ON metrics(agent_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp);
