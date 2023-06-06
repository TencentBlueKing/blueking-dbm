package native

import (
	"fmt"
	"regexp"
)

// TdbctlDbWork TODO
type TdbctlDbWork struct {
	DbWorker
}

// Server TODO
type Server struct {
	ServerName string `db:"Server_name"`
	Host       string `db:"Host"`
	Db         string `db:"Db"`
	Username   string `db:"Username"`
	Password   string `db:"Password"`
	Port       int    `db:"Port"`
	Wrapper    string `db:"Wrapper"`
}

// GetConn TODO
func (s *Server) GetConn() (conn *DbWorker, err error) {
	return InsObject{
		Host: s.Host,
		Port: s.Port,
		User: s.Username,
		Pwd:  s.Password,
	}.Conn()
}

// GetEndPoint TODO
func (s *Server) GetEndPoint() string {
	return fmt.Sprintf("%s:%d", s.Host, s.Port)
}

// GetAlterNodeSql TODO
//
//	"tdbctl create node wrapper 'mysql_slave' options(user '%s', password '%s', host '%s', port %d, number %d);",
func (s *Server) GetAlterNodeSql(serverName string) (sqlStr string) {
	return fmt.Sprintf("TDBCTL ALTER NODE %s options(user '%s', password '%s', host '%s', port %d);",
		serverName,
		s.Username,
		s.Password, s.Host, s.Port)
}

// SHARDPREFIX TODO
const (
	SHARDPREFIX         = "SPT"
	SLAVE_SHARDPREFIX   = "SPT_SLAVE"
	SPIDER_PREFIX       = "SPIDER"
	SPIDER_SLAVE_PREFIX = "SPIDER_SLAVE"
)

// SvrNameIsMasterShard TODO
func SvrNameIsMasterShard(svrName string) bool {
	m := regexp.MustCompile(fmt.Sprintf(`%s\d+`, SHARDPREFIX))
	return m.MatchString(svrName)
}

// SvrNameIsSlaveShard TODO
func SvrNameIsSlaveShard(svrName string) bool {
	m := regexp.MustCompile(fmt.Sprintf(`%s\d+`, SLAVE_SHARDPREFIX))
	return m.MatchString(svrName)
}

// SvrNameIsSlaveSpiderShard TODO
func SvrNameIsSlaveSpiderShard(svrName string) bool {
	m := regexp.MustCompile(fmt.Sprintf(`%s\d+`, SPIDER_SLAVE_PREFIX))
	return m.MatchString(svrName)
}

// GetMasterShardNameByShardNum TODO
func GetMasterShardNameByShardNum(num string) string {
	return SPIDER_PREFIX + num
}

// GetSlaveShardNameByShardNum TODO
func GetSlaveShardNameByShardNum(num string) string {
	return SPIDER_SLAVE_PREFIX + num
}

// GetSlaveShardNameByMasterShardName TODO
func GetSlaveShardNameByMasterShardName(masterShardName string) string {
	num := GetShardNumberFromMasterServerName(masterShardName)
	return GetSlaveShardNameByShardNum(num)
}

// GetShardNumberFromMasterServerName TODO
func GetShardNumberFromMasterServerName(serverName string) string {
	m := regexp.MustCompile(SHARDPREFIX)
	return m.ReplaceAllString(serverName, "")
}

// GetShardNumberFromSlaveServerName TODO
func GetShardNumberFromSlaveServerName(serverName string) string {
	m := regexp.MustCompile(SLAVE_SHARDPREFIX)
	return m.ReplaceAllString(serverName, "")
}

// AlterNode TODO
func (t *TdbctlDbWork) AlterNode(server_name string, user, password, host string, port int) (int64, error) {
	return t.Exec("tdbctl alter node  ? options(user ?,password ?,host ?,port ?)", server_name, user, password, host,
		port)
}

// SelectServers TODO
func (t *TdbctlDbWork) SelectServers() (servers []Server, err error) {
	err = t.Queryx(&servers, "select * from  mysql.servers")
	return
}

// get_exec_special_node_cmd TODO
func (t *TdbctlDbWork) get_exec_special_node_cmd(serverName string) string {
	return fmt.Sprintf("TDBCTL CONNECT NODE %s EXECUTE", serverName)
}

// GetSingleGlobalVar TODO
func (t *TdbctlDbWork) GetSingleGlobalVar(serverName, varName string) (val string, err error) {
	var item MySQLGlobalVariableItem
	if err = t.Queryxs(&item, fmt.Sprintf("%s 'show global variables like \"%s\"'", t.get_exec_special_node_cmd(
		serverName), varName)); err != nil {
		return "", err
	}
	return item.Value, nil
}

// QueryGlobalVariables TODO
func (t *TdbctlDbWork) QueryGlobalVariables(serverName string) (map[string]string, error) {
	result := make(map[string]string)
	rows, err := t.Db.Query(fmt.Sprintf(" %s 'SHOW GLOBAL VARIABLES'", t.get_exec_special_node_cmd(
		serverName)))
	if err != nil {
		return result, err
	}
	defer rows.Close()
	for rows.Next() {
		var key, val string
		err := rows.Scan(&key, &val)
		if err != nil {
			continue
		}
		result[key] = val
	}
	return result, nil
}

// MySQLVarsCompare TODO
func (h *TdbctlDbWork) MySQLVarsCompare(serverName string, referInsConn *DbWorker, checkVars []string) (err error) {
	referVars, err := referInsConn.QueryGlobalVariables()
	if err != nil {
		return err
	}
	compareVars, err := h.QueryGlobalVariables(serverName)
	if err != nil {
		return err
	}
	return compareDbVariables(referVars, compareVars, checkVars)
}

// ShowSlaveStatus TODO
func (t *TdbctlDbWork) ShowSlaveStatus(serverName string) (data ShowSlaveStatusResp, err error) {
	err = t.Queryxs(&data, fmt.Sprintf("%s 'show slave status'", t.get_exec_special_node_cmd(serverName)))
	return
}

// ShowMasterStatus TODO
func (t *TdbctlDbWork) ShowMasterStatus(serverName string) (data MasterStatusResp, err error) {
	err = t.Queryxs(&data, fmt.Sprintf("%s 'show master status'", t.get_exec_special_node_cmd(serverName)))
	return
}

// LockTables TODO
func (t *TdbctlDbWork) LockTables(serverName string) (data MasterStatusResp, err error) {
	_, err = t.Exec(fmt.Sprintf("%s 'lock table with read lock'", t.get_exec_special_node_cmd(serverName)))
	return
}
