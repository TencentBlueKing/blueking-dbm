SET SESSION sql_log_bin = 0;
-- 授权, 检查 ERROR_MSG 来判断是否成功
-- ERROR STATE CODE
-- 32401 参数验证错误
-- 32402 冲突检测错误
-- 中控不会转发授权语句, 当普通 MySQL 就好
DROP PROCEDURE IF EXISTS infodba_schema.dba_grant;
DELIMITER //
CREATE PROCEDURE infodba_schema.dba_grant(
    IN username VARCHAR(128), 
    IN ip_list VARCHAR(3000), -- 但是限制最大只能传入 2000
    IN db_list VARCHAR(3000), -- 但是限制最大只能传入 2000
    IN long_psw VARCHAR(128), -- 密码是密文
    IN short_psw VARCHAR(32), -- 密码是密文
    IN priv_str VARCHAR(4096), 
    IN global_priv_str VARCHAR(4096)
)
SQL SECURITY INVOKER
BEGIN
    IF LENGTH(ip_list) >= 2000 OR LENGTH(db_list) >= 2000 THEN
        SIGNAL SQLSTATE '32401' SET MESSAGE_TEXT = "input ip_list or db_list too long, max length is 2000";
    END IF;

    IF NOT(long_psw LIKE '*%' AND LENGTH(long_psw) = 41) THEN
        SET @msg = CONCAT('bad password: ', long_psw);
        SIGNAL SQLSTATE '32401' SET MESSAGE_TEXT = @msg;
    END IF;

    -- 不同版本授权语句不兼容, 所以干脆不写
    SET SESSION sql_log_bin = 0;

    -- 初始化结果表
    CALL init_report_table();

    -- 初始化结果标识
    SET @uuid = UUID();
    SET @grant_time = NOW();
    
    SET ip_list = TRIM(BOTH ',' FROM ip_list);
    SET ip_list = CONCAT(ip_list, ",");

    SET db_list = TRIM(BOTH ',' FROM db_list);
    SET db_list = CONCAT(db_list, ",");    

    -- 先做检查
    SET @is_check_failed = 0;
    CALL check_all(@uuid, @grant_time, username, ip_list, db_list, long_psw, short_psw, @is_check_failed);

    IF @is_check_failed = 1 THEN
        SIGNAL SQLSTATE '32402' SET MESSAGE_TEXT = @uuid;
    END IF;

    WHILE (LOCATE(',', ip_list) > 0)
    DO
        SET @ip = TRIM(SUBSTRING(ip_list, 1, LOCATE(',', ip_list) - 1));
        SET ip_list = SUBSTRING(ip_list, LOCATE(',', ip_list) + 1);
        -- 如果涉及新增账号, 只使用新版本密码
        CALL dba_grant_one_ip(username, @ip, db_list, long_psw, priv_str, global_priv_str);
    END WHILE;

    FLUSH PRIVILEGES;
END//
DELIMITER ;

DROP PROCEDURE IF EXISTS infodba_schema.init_report_table;
DROP TABLE IF EXISTS infodba_schema.dba_grant_result;
DELIMITER //
CREATE PROCEDURE infodba_schema.init_report_table()
SQL SECURITY INVOKER
BEGIN
    -- 不同版本授权语句不兼容, 所以干脆不写
    SET SESSION sql_log_bin = 0;

    CREATE TABLE IF NOT EXISTS infodba_schema.dba_grant_result(
        id VARCHAR(64),
        grant_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        username VARCHAR(128),
        client_ip VARCHAR(32),
        dbname VARCHAR(64),
        long_psw VARCHAR(128),
        short_psw VARCHAR(32),
        priv VARCHAR(4096),
        global_priv VARCHAR(4096),
        msg VARCHAR(4096)
    ) ENGINE = InnoDB;
    DELETE FROM dba_grant_result WHERE grant_time < DATE_SUB(NOW(), INTERVAL 1 DAY);
END//
DELIMITER ;

-- 检查入口
DROP PROCEDURE IF EXISTS infodba_schema.check_all;
DELIMITER //
CREATE PROCEDURE infodba_schema.check_all(
    IN uuid VARCHAR(64),
    IN grant_time TIMESTAMP,
    IN username VARCHAR(128), 
    IN ip_list VARCHAR(3000), 
    IN db_list VARCHAR(3000), 
    IN long_psw VARCHAR(128),
    IN short_psw VARCHAR(32),
    OUT is_check_failed INT
)
SQL SECURITY INVOKER
BEGIN
    -- 全量检查入口
    CALL check_password(uuid, grant_time, username, ip_list, long_psw, short_psw, is_check_failed);
    CALL check_db_conflict(uuid, grant_time, username, ip_list, db_list, is_check_failed);
END //
DELIMITER ;

-- 密码一致性检查
DROP PROCEDURE IF EXISTS infodba_schema.check_password;
DELIMITER //
CREATE PROCEDURE infodba_schema.check_password(
    IN uuid VARCHAR(64),
    IN grant_time TIMESTAMP,    
    IN username VARCHAR(128), 
    IN ip_list VARCHAR(3000), 
    IN long_psw VARCHAR(128),
    IN short_psw VARCHAR(32),
    OUT is_check_failed INT
)
SQL SECURITY INVOKER
BEGIN
    -- 不同版本授权语句不兼容, 所以干脆不写
    SET SESSION sql_log_bin = 0;

    WHILE (LOCATE(',', ip_list) > 0)
    DO
        SET @ip = TRIM(SUBSTRING(ip_list, 1, LOCATE(',', ip_list) - 1));
        SET ip_list = SUBSTRING(ip_list, LOCATE(',', ip_list) + 1);  

        SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = username AND host = @ip) INTO @user_host_exists;
        IF @user_host_exists THEN
            -- 用户存在, 检查密码
            -- 5.6 及之前还有 old_password 函数, 也就是 < 5.7 可能有 old_password
            IF SUBSTRING_INDEX(@@version, ".", 2) < 5.7 THEN
                SELECT password = long_psw OR password = short_psw INTO @psw_match FROM mysql.user WHERE user = username AND host = @ip;
            ELSE
                SELECT authentication_string = long_psw INTO @psw_match FROM mysql.user WHERE user = username AND host =@ip;
            END IF;   

            IF NOT @psw_match THEN
                SET is_check_failed = is_check_failed OR 1;
                INSERT INTO dba_grant_result(id, grant_time, username, client_ip, long_psw, short_psw, msg)
                    VALUES (uuid, grant_time, username, @ip, long_psw, short_psw, 'password not match');
            END IF;     
        END IF;
    END WHILE;
END //
DELIMITER ;

-- 库模式冲突检查入口
DROP PROCEDURE IF EXISTS infodba_schema.check_db_conflict;
DELIMITER //
CREATE PROCEDURE infodba_schema.check_db_conflict(
    IN uuid VARCHAR(64),
    IN grant_time TIMESTAMP,
    IN username VARCHAR(128), 
    IN ip_list VARCHAR(3000), 
    IN db_list VARCHAR(3000),
    OUT is_check_failed INT
)
SQL SECURITY INVOKER
BEGIN
    WHILE (LOCATE(',', ip_list) > 0)
    DO
        SET @ip = TRIM(SUBSTRING(ip_list, 1, LOCATE(',', ip_list) - 1));
        SET ip_list = SUBSTRING(ip_list, LOCATE(',', ip_list) + 1);  

        SELECT EXISTS(SELECT 1 FROM mysql.db WHERE user = username AND host = @ip) INTO @db_priv_applied;
        IF @db_priv_applied THEN
            CALL check_db_conflict_one_ip(uuid, grant_time, username, @ip, db_list, is_check_failed);
        END IF;
    END WHILE;
END //
DELIMITER ;

-- 单 IP 库模式冲突检查
DROP PROCEDURE IF EXISTS infodba_schema.check_db_conflict_one_ip;
DELIMITER //
CREATE PROCEDURE infodba_schema.check_db_conflict_one_ip(
    IN uuid VARCHAR(64),
    IN grant_time TIMESTAMP,    
    IN username VARCHAR(128), 
    IN ip VARCHAR(15), 
    IN db_list VARCHAR(3000),
    OUT is_check_failed INT
)
SQL SECURITY INVOKER
BEGIN
    DECLARE applied_dbname VARCHAR(64);
    DECLARE cursor_done INT DEFAULT FALSE;
    DECLARE db_cursor CURSOR FOR SELECT db FROM mysql.db WHERE user = username AND host = @ip;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET cursor_done = TRUE;    

    -- 不同版本授权语句不兼容, 所以干脆不写
    SET SESSION sql_log_bin = 0;

    OPEN db_cursor;
    fetch_loop: LOOP
        FETCH db_cursor INTO applied_dbname;
        IF cursor_done THEN
            LEAVE fetch_loop;
        END IF;

        SET @loop_db_list = db_list;

        WHILE (LOCATE(',', @loop_db_list) > 0)
        DO
            SET @dbname = TRIM(SUBSTRING(@loop_db_list, 1, LOCATE(',', @loop_db_list) - 1));
            SET @loop_db_list = SUBSTRING(@loop_db_list, LOCATE(',', @loop_db_list) + 1);

            -- 申请库名和已有库名不等并且能模式匹配 
            IF @dbname <> applied_dbname AND (@dbname LIKE applied_dbname OR applied_dbname LIKE @dbname) THEN 
                SET is_check_failed = is_check_failed OR 1;
                INSERT INTO dba_grant_result(id, grant_time, username, client_ip, dbname, long_psw, short_psw, msg)
                    VALUES (uuid, grant_time, username, @ip, @dbname, long_psw, short_psw, CONCAT("conflict with applied db [", applied_dbname, "]"));
            END IF;
        END WHILE;

    END LOOP fetch_loop;
    CLOSE db_cursor;
END //
DELIMITER ;

-- 单 IP 授权
DROP PROCEDURE IF EXISTS infodba_schema.dba_grant_one_ip;
DELIMITER //
CREATE PROCEDURE infodba_schema.dba_grant_one_ip(
    IN username VARCHAR(128), 
    IN ip VARCHAR(15), 
    IN db_list VARCHAR(3000), 
    IN psw VARCHAR(128), 
    IN priv_str VARCHAR(4096), 
    IN global_priv_str VARCHAR(4096)
)
SQL SECURITY INVOKER
BEGIN
    -- 不同版本授权语句不兼容, 所以干脆不写
    SET SESSION sql_log_bin = 0;

    SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = username AND host = ip) INTO @user_host_exists;
    IF NOT @user_host_exists THEN
        -- 用户不存在, 直接创建, 只使用新版本密码, 传入的密码是密文
        IF SUBSTRING_INDEX(@@version, ".", 2) < 5.7 THEN
            SET @create_user_sql = CONCAT("GRANT USAGE ON *.* TO '", username, "'@'", ip, "' IDENTIFIED BY PASSWORD '", psw, "'");
            PREPARE stmt FROM @create_user_sql;
            EXECUTE stmt;
        ELSE
            SET @create_user_sql = CONCAT("CREATE USER IF NOT EXISTS '", username, "'@'", ip, "' IDENTIFIED WITH mysql_native_password AS '", psw, "'");
            PREPARE stmt FROM @create_user_sql;
            EXECUTE stmt;            
        END IF;
    END IF;

    WHILE (LOCATE(',', db_list) > 0)
    DO
        SET @db = TRIM(SUBSTRING(db_list, 1, LOCATE(',', db_list) - 1));
        SET db_list = SUBSTRING(db_list, LOCATE(',', db_list) + 1);
        CALL dba_grant_one_ip_db(username, ip, @db, psw, priv_str, global_priv_str);
    END WHILE;
END//
DELIMITER ;

-- 单 IP 单 DB 授权
DROP PROCEDURE IF EXISTS infodba_schema.dba_grant_one_ip_db;
DELIMITER //
CREATE PROCEDURE infodba_schema.dba_grant_one_ip_db(
    IN username VARCHAR(128), 
    IN ip VARCHAR(15), 
    IN dbname VARCHAR(64), 
    IN psw VARCHAR(128), 
    IN priv_str VARCHAR(4096), 
    IN global_priv_str VARCHAR(4096)
)
SQL SECURITY INVOKER
BEGIN
    DECLARE exists_db VARCHAR(64);
    DECLARE cursor_done INT DEFAULT FALSE;
    DECLARE db_cursor CURSOR FOR SELECT db FROM mysql.db WHERE user = username AND host = ip;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET cursor_done = TRUE;

    -- 不同版本授权语句不兼容, 所以干脆不写
    SET SESSION sql_log_bin = 0;

    SET priv_str = TRIM(BOTH ',' FROM TRIM(priv_str));
    SET global_priv_str = TRIM(BOTH ',' FROM TRIM(global_priv_str));

    -- 全局权限
    IF global_priv_str IS NOT NULL AND global_priv_str <> '' THEN
        SET @global_grant_sql = CONCAT("GRANT ", global_priv_str, " ON *.* TO '", username, "'@'", ip, "'");
        PREPARE stmt FROM @global_grant_sql;
        EXECUTE stmt;
    END IF;

    -- 非全局权限
    IF priv_str IS NOT NULL AND priv_str <> '' THEN
        SET @grant_sql = "";
        if dbname = '*' OR dbname = '%' THEN
            SET @grant_sql = CONCAT("GRANT ", priv_str, " ON *.* TO '", username, "'@'", ip, "'");
        ELSE
            SET @grant_sql = CONCAT("GRANT ", priv_str, " ON `", dbname, "`.* TO '", username, "'@'", ip, "'");
        END IF;
        PREPARE stmt FROM @grant_sql;
        EXECUTE stmt;
    END IF;
END//
DELIMITER ;
