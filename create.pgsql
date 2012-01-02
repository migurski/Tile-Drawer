DROP TABLE IF EXISTS extracts;
DELETE FROM geometry_columns WHERE f_table_name = 'extracts';



CREATE TABLE extracts
(
    href    VARCHAR(128) PRIMARY KEY,
    size    BIGINT,
    date    VARCHAR(32)

);

SELECT AddGeometryColumn('extracts', 'geom', 4326, 'MULTIPOLYGON', 2);