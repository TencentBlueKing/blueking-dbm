package dbmysql

import (
	"database/sql"
	"fmt"

	"dbm-services/common/dbha/ha-module/log"

	_ "github.com/go-sql-driver/mysql" // mysql TODO
)

// ConnectAdminProxy use admin port to connect proxy
func ConnectAdminProxy(user, password, address string) (*sql.DB, error) {
	config := fmt.Sprintf("%s:%s@tcp(%s)/?timeout=5s&maxAllowedPacket=%s",
		user,
		password,
		address,
		"4194304")
	db, err := sql.Open("mysql", config)
	if err != nil {
		log.Logger.Errorf("Database connection failed. user: %s, address: %v,err:%s.", user,
			address, err.Error())
		return nil, err
	}
	if _, err = db.Query("select version();"); err != nil {
		log.Logger.Errorf("Check Database connection failed. user: %s, address: %v,err:%s.", user,
			address, err.Error())
		return nil, err
	}

	return db, nil
}

// SwitchProxyBackendAddress connect proxy and refresh backends
func SwitchProxyBackendAddress(proxyIp string, proxyAdminPort int, proxyUser string, proxyPass string,
	slaveIp string, slavePort int) error {
	addr := fmt.Sprintf("%s:%d", proxyIp, proxyAdminPort)
	db, err := ConnectAdminProxy(proxyUser, proxyPass, addr)
	if err != nil {
		log.Logger.Errorf("connect admin proxy failed. addr:%s, err:%s", addr, err.Error())
		return fmt.Errorf("connect admin proxy failed")
	}

	switchSql := fmt.Sprintf("refresh_backends('%s:%d',1)", slaveIp, slavePort)
	querySql := "select * from backends"

	_, err = db.Exec(switchSql)
	if err != nil {
		log.Logger.Errorf("exec switch sql failed. err:%s", err.Error())
		return fmt.Errorf("exec switch sql failed")
	}

	var (
		backendIndex    int
		address         string
		state           string
		backendType     string
		uuid            []uint8
		connectedClient int
	)

	rows, err := db.Query(querySql)
	if err != nil {
		log.Logger.Errorf("query backend failed. err:%s", err.Error())
		return fmt.Errorf("query backen failed")
	}
	for rows.Next() {
		err = rows.Scan(&backendIndex, &address, &state, &backendType, &uuid, &connectedClient)
		if err != nil {
			log.Logger.Errorf("scan rows failed. err:%s", err.Error())
			return fmt.Errorf("scan rows failed")
		}
		if address == fmt.Sprintf("%s:%d", slaveIp, slavePort) {
			log.Logger.Infof("%s:%d refresh backend to %s is working", proxyIp, proxyAdminPort, slaveIp)
			if address != "1.1.1.1:3306" {
				if state == "up" || state == "unknown" {
					// update cmdb backend
					// update binlog format
					return nil
				}
			}
			return nil
		}
	}
	log.Logger.Errorf("%s:%d refresh backend to %s failed", proxyIp, proxyAdminPort, slaveIp)
	return fmt.Errorf("%s:%d refresh backend to %s failed", proxyIp, proxyAdminPort, slaveIp)
}
