-- campaign schema (run order: 1 — no dependencies)

CREATE TABLE campaign.campaign_channels (
    channel_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    channel_name    VARCHAR(50) NOT NULL,
    channel_type    VARCHAR(30) NOT NULL
);
COMMENT ON COLUMN campaign.campaign_channels.channel_type IS 'Digital, Print, Social, Email, TV';

CREATE TABLE campaign.campaigns (
    campaign_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_name   VARCHAR(100) NOT NULL,
    channel_id      INTEGER REFERENCES campaign.campaign_channels(channel_id),
    start_date      DATE NOT NULL,
    end_date        DATE,
    budget          DECIMAL(12,2) NOT NULL,
    status          VARCHAR(20) NOT NULL
);
COMMENT ON COLUMN campaign.campaigns.status IS 'Planned, Active, Paused, Completed';

CREATE TABLE campaign.campaign_performance (
    perf_id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id     INTEGER NOT NULL REFERENCES campaign.campaigns(campaign_id),
    perf_date       DATE NOT NULL,
    impressions     INTEGER DEFAULT 0,
    clicks          INTEGER DEFAULT 0,
    spend           DECIMAL(10,2) DEFAULT 0
);
