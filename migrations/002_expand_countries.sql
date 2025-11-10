-- Migration: Expand country list from 15 to 50 countries
-- Date: 2025-11-09
-- Description: Adds 35 more countries for better global coverage and more event data

-- Additional countries (balanced by region and democracy level)
INSERT INTO countries (name, iso_code) VALUES
    -- Latin America (high activity regions)
    ('Brazil', 'BRA'),
    ('Mexico', 'MEX'),
    ('Argentina', 'ARG'),
    ('Chile', 'CHL'),
    ('Colombia', 'COL'),
    ('Peru', 'PER'),
    ('Venezuela', 'VEN'),

    -- Asia-Pacific (major democracies and transitions)
    ('India', 'IND'),
    ('Indonesia', 'IDN'),
    ('Philippines', 'PHL'),
    ('Thailand', 'THA'),
    ('Malaysia', 'MYS'),
    ('Taiwan', 'TWN'),
    ('Singapore', 'SGP'),

    -- Eastern Europe (democratic transitions)
    ('Poland', 'POL'),
    ('Czech Republic', 'CZE'),
    ('Hungary', 'HUN'),
    ('Romania', 'ROU'),
    ('Ukraine', 'UKR'),

    -- Middle East & North Africa
    ('Israel', 'ISR'),
    ('Turkey', 'TUR'),
    ('Tunisia', 'TUN'),
    ('Egypt', 'EGY'),

    -- Sub-Saharan Africa
    ('South Africa', 'ZAF'),
    ('Nigeria', 'NGA'),
    ('Kenya', 'KEN'),
    ('Ghana', 'GHA'),
    ('Ethiopia', 'ETH'),

    -- Western Europe (additional)
    ('Spain', 'ESP'),
    ('Italy', 'ITA'),
    ('Portugal', 'PRT'),
    ('Belgium', 'BEL'),
    ('Austria', 'AUT'),
    ('Ireland', 'IRL'),
    ('Greece', 'GRC')

ON CONFLICT (iso_code) DO NOTHING;

-- Note: Now have 50 countries total:
-- Original 15 + New 35 = 50 countries
-- Covers all regions, democracy levels, and high-activity areas
