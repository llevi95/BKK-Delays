-- ============================================================
-- candidate_db one-time setup
-- Runs automatically on first container start via entrypoint.sh
-- Idempotent: safe to re-run on subsequent starts
-- ============================================================

-- Create the database
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'candidate_db')
BEGIN
    CREATE DATABASE candidate_db;
END
GO

-- Create the server-level login
IF NOT EXISTS (SELECT name FROM sys.server_principals WHERE name = N'candidate')
BEGIN
    CREATE LOGIN [candidate] WITH PASSWORD = N'HwC4ndidate#2026';
END
GO

USE candidate_db;
GO

-- Create the database user mapped to the login
IF NOT EXISTS (SELECT name FROM sys.database_principals WHERE name = N'candidate')
BEGIN
    CREATE USER [candidate] FOR LOGIN [candidate];
END
GO

-- db_owner lets the candidate: CREATE SCHEMA, CREATE TABLE, INSERT/UPDATE/DELETE
ALTER ROLE db_owner ADD MEMBER [candidate];
GO

PRINT 'Setup complete: candidate_db ready, candidate user provisioned.';
GO
