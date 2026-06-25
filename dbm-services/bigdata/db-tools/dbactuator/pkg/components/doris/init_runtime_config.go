package doris

import (
	"database/sql"
	"fmt"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/dorisutil"
	"dbm-services/common/go-pubpkg/logger"
)

// InitRuntimeConfigParams 初始化运行时配置参数
type InitRuntimeConfigParams struct {
	Host            string                            `json:"host" validate:"required,ip"` // FE节点IP
	QueryPort       int                               `json:"query_port" validate:"required"`
	UserName        string                            `json:"username"`
	Password        string                            `json:"password"`
	RootPassword    string                            `json:"root_password"`
	AdminPassword   string                            `json:"admin_password"`
	GlobalVariables map[string]string                 `json:"global_variables"` // 全局变量 key=value
	UserProperties  map[string]map[string]interface{} `json:"user_properties"`  // 用户属性 username -> key -> value
	WorkloadGroups  map[string]map[string]interface{} `json:"workload_groups"`  // 资源组 group_name -> key -> value
}

// InitRuntimeConfigService 初始化运行时配置服务
type InitRuntimeConfigService struct {
	GeneralParam    *components.GeneralParam
	Params          *InitRuntimeConfigParams
	RollBackContext rollback.RollBackObjects
}

// escapeSingleQuote 转义单引号 ' -> ”
func escapeSingleQuote(s string) string {
	return strings.ReplaceAll(s, "'", "''")
}

// getDB 获取数据库连接
func (i *InitRuntimeConfigService) getDB() (*sql.DB, error) {
	rootPwd := dorisutil.DefaultString(i.Params.RootPassword, i.Params.Password)
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/", RootUser, rootPwd, i.Params.Host, i.Params.QueryPort)
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		logger.Error("连接Doris数据库失败，%v", err)
		return nil, err
	}
	return db, nil
}

// InitRuntimeConfig 初始化Doris运行时配置（全局变量、用户属性、资源组）
// 注意：SET GLOBAL / CREATE WORKLOAD GROUP 是 DDL，不能放在事务里
func (i *InitRuntimeConfigService) InitRuntimeConfig() (err error) {
	db, err := i.getDB()
	if err != nil {
		return err
	}
	defer db.Close()

	// 1. 全局变量 SET GLOBAL — DDL，逐条自动提交
	if err = i.applyGlobalVariables(db); err != nil {
		return err
	}

	// 2. 资源组 CREATE/ALTER WORKLOAD GROUP — 必须在用户属性之前
	//    因为 default_workload_group 等属性引用的资源组需要先存在
	if err = i.applyWorkloadGroups(db); err != nil {
		return err
	}

	// 3. 用户属性 SET PROPERTY — 逐条执行
	if err = i.applyUserProperties(db); err != nil {
		return err
	}

	logger.Info("初始化运行时配置成功")
	return nil
}

// applyGlobalVariables 逐条执行 SET GLOBAL
func (i *InitRuntimeConfigService) applyGlobalVariables(db *sql.DB) error {
	for varName, varValue := range i.Params.GlobalVariables {
		sqlStr := fmt.Sprintf("SET GLOBAL `%s` = '%s'", varName, escapeSingleQuote(varValue))
		logger.Info("执行全局变量: %s", sqlStr)
		if _, err := db.Exec(sqlStr); err != nil {
			logger.Error("SET GLOBAL %s = '%s' 失败: %v", varName, varValue, err)
			return fmt.Errorf("SET GLOBAL %s = '%s' 失败: %w", varName, varValue, err)
		}
	}
	return nil
}

// applyUserProperties 逐条执行 SET PROPERTY FOR
func (i *InitRuntimeConfigService) applyUserProperties(db *sql.DB) error {
	for userName, props := range i.Params.UserProperties {
		for propKey, propValue := range props {
			strValue := formatValue(propValue)
			if strValue == "" {
				continue
			}
			sqlStr := fmt.Sprintf("SET PROPERTY FOR '%s' '%s' = '%s'",
				escapeSingleQuote(userName),
				escapeSingleQuote(propKey),
				escapeSingleQuote(strValue),
			)
			logger.Info("执行用户属性: %s", sqlStr)
			if _, err := db.Exec(sqlStr); err != nil {
				logger.Error("SET PROPERTY FOR '%s' '%s' = '%s' 失败: %v", userName, propKey, strValue, err)
				return fmt.Errorf("SET PROPERTY FOR '%s' '%s' = '%s' 失败: %w", userName, propKey, strValue, err)
			}
		}
	}
	return nil
}

// getExistingWorkloadGroups 查询当前已存在的资源组名称集合
func (i *InitRuntimeConfigService) getExistingWorkloadGroups(db *sql.DB) (map[string]bool, error) {
	rows, err := db.Query("SHOW WORKLOAD GROUPS")
	if err != nil {
		logger.Error("查询已有资源组失败: %v", err)
		return nil, fmt.Errorf("SHOW WORKLOAD GROUPS 失败: %w", err)
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, fmt.Errorf("获取列信息失败: %w", err)
	}

	// 找到 Name 列的索引，适配不同 Doris 版本的列结构
	nameIdx := -1
	for i, col := range columns {
		if strings.EqualFold(col, "Name") {
			nameIdx = i
			break
		}
	}
	if nameIdx == -1 {
		return nil, fmt.Errorf("SHOW WORKLOAD GROUPS 结果中未找到 Name 列, columns=%v", columns)
	}

	existing := make(map[string]bool)
	values := make([]interface{}, len(columns))
	valuePtrs := make([]interface{}, len(columns))
	for i := range columns {
		valuePtrs[i] = &values[i]
	}
	for rows.Next() {
		if err := rows.Scan(valuePtrs...); err != nil {
			logger.Error("扫描资源组行失败: %v", err)
			return nil, fmt.Errorf("扫描资源组行失败: %w", err)
		}
		switch v := values[nameIdx].(type) {
		case []byte:
			existing[string(v)] = true
		}
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("遍历资源组结果失败: %w", err)
	}
	return existing, nil
}

// applyWorkloadGroups 逐条执行 CREATE/ALTER WORKLOAD GROUP
func (i *InitRuntimeConfigService) applyWorkloadGroups(db *sql.DB) error {
	existingGroups, err := i.getExistingWorkloadGroups(db)
	if err != nil {
		return err
	}
	logger.Info("已有资源组: %v", existingGroups)

	for groupName, props := range i.Params.WorkloadGroups {
		exists := existingGroups[groupName]
		if err := i.applyWorkloadGroup(db, groupName, props, exists); err != nil {
			return err
		}
	}
	return nil
}

// 过滤列表 — 暂时跳过这些属性
var skipWorkloadGroupProps = map[string]bool{
	"compute_group": true, // 存算分离架构
}

// formatValue 将 interface{} 格式化为字符串，避免 float64 大整数变成科学计数法
func formatValue(v interface{}) string {
	if f, ok := v.(float64); ok && f == float64(int64(f)) {
		return fmt.Sprintf("%d", int64(f))
	}
	return fmt.Sprintf("%v", v)
}

// applyWorkloadGroup 创建或更新单个资源组配置
func (i *InitRuntimeConfigService) applyWorkloadGroup(db *sql.DB, groupName string, props map[string]interface{}, exists bool) error {
	var propPairs []string
	for key, value := range props {
		strValue := formatValue(value)
		if strValue == "" {
			continue
		}
		if skipWorkloadGroupProps[key] {
			continue
		}
		propPairs = append(propPairs, fmt.Sprintf(`"%s" = "%s"`,
			escapeSingleQuote(key),
			escapeSingleQuote(strValue),
		))
	}
	propertiesStr := strings.Join(propPairs, ",\n    ")

	if exists {
		alterSql := fmt.Sprintf("ALTER WORKLOAD GROUP `%s` PROPERTIES (\n    %s\n);", groupName, propertiesStr)
		logger.Info("更新资源组: %s", alterSql)
		if _, err := db.Exec(alterSql); err != nil {
			logger.Error("ALTER WORKLOAD GROUP %s 失败: %v", groupName, err)
			return fmt.Errorf("ALTER WORKLOAD GROUP %s 失败: %w", groupName, err)
		}
	} else {
		createSql := fmt.Sprintf("CREATE WORKLOAD GROUP `%s` PROPERTIES (\n    %s\n);", groupName, propertiesStr)
		logger.Info("创建资源组: %s", createSql)
		if _, err := db.Exec(createSql); err != nil {
			logger.Error("CREATE WORKLOAD GROUP %s 失败: %v", groupName, err)
			return fmt.Errorf("CREATE WORKLOAD GROUP %s 失败: %w", groupName, err)
		}
	}

	return nil
}
