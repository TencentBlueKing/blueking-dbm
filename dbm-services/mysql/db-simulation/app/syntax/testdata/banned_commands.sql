-- 测试禁用命令
USE test_db;
-- GRANT - 禁用
GRANT SELECT,
    INSERT ON test_db.* TO 'testuser' @'localhost';
-- GRANT ALL - 禁用
GRANT ALL PRIVILEGES ON *.* TO 'admin' @'%' IDENTIFIED BY 'password';
-- REVOKE - 禁用
REVOKE
SELECT ON test_db.*
FROM 'testuser' @'localhost';
-- REVOKE ALL - 禁用
REVOKE ALL PRIVILEGES ON *.*
FROM 'testuser' @'localhost';
-- CREATE USER - 禁用
CREATE USER 'newuser' @'localhost' IDENTIFIED BY 'password123';
-- DROP USER - 禁用
DROP USER IF EXISTS 'olduser' @'localhost';
-- ALTER USER - 禁用
ALTER USER 'testuser' @'localhost' IDENTIFIED BY 'newpassword';
-- KILL - 禁用
KILL 12345;
-- KILL CONNECTION - 禁用
KILL CONNECTION 12345;
-- KILL QUERY - 禁用
KILL QUERY 12345;
-- RESET - 禁用
RESET MASTER;
-- RESET SLAVE - 禁用
RESET SLAVE;
-- SHUTDOWN - 禁用
SHUTDOWN;
-- PURGE - 禁用
PURGE BINARY LOGS BEFORE '2023-01-01 00:00:00';
-- INSTALL PLUGIN - 禁用
INSTALL PLUGIN rpl_semi_sync_master SONAME 'semisync_master.so';
-- UNINSTALL PLUGIN - 禁用
UNINSTALL PLUGIN rpl_semi_sync_master;
-- SLAVE START - 禁用
START SLAVE;
-- SLAVE STOP - 禁用
STOP SLAVE;
-- CHANGE MASTER - 禁用
CHANGE MASTER TO MASTER_HOST = '192.168.1.1',
MASTER_USER = 'repl',
MASTER_PASSWORD = 'password';
-- START GROUP REPLICATION - 禁用
START GROUP_REPLICATION;
-- STOP GROUP REPLICATION - 禁用
STOP GROUP_REPLICATION;
-- SET PASSWORD - 禁用
SET PASSWORD FOR 'user' @'localhost' = PASSWORD('newpass');