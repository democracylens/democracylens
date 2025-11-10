-- Cleanup Script: Remove ACLED Events from Database
-- Run this script to remove all ACLED data from the events table
-- Date: 2025-01-09

-- Display count of ACLED events before deletion
SELECT 'ACLED events before deletion:' as info, COUNT(*) as count
FROM events
WHERE source = 'ACLED';

-- Delete all ACLED events
DELETE FROM events WHERE source = 'ACLED';

-- Display count of remaining events after deletion
SELECT 'Total events remaining after deletion:' as info, COUNT(*) as count
FROM events;

-- Optional: Display breakdown of remaining events by source
SELECT source, COUNT(*) as count
FROM events
GROUP BY source
ORDER BY source;
