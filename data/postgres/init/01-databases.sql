-- Comet
CREATE ROLE comet LOGIN PASSWORD 'CHANGE_ME_POSTGRES_PASSWORD';
ALTER ROLE comet SET synchronous_commit = off;
ALTER ROLE comet SET work_mem = '16MB';
CREATE DATABASE comet OWNER comet;

-- StremThru
CREATE ROLE stremthru LOGIN PASSWORD 'CHANGE_ME_POSTGRES_PASSWORD';
ALTER ROLE stremthru SET synchronous_commit = off;
CREATE DATABASE stremthru OWNER stremthru;

-- AIOManager
CREATE ROLE aiomanager LOGIN PASSWORD 'CHANGE_ME_POSTGRES_PASSWORD';
CREATE DATABASE aiomanager OWNER aiomanager;
