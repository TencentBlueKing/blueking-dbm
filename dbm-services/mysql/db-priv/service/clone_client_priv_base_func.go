package service

import (
	"context"
	"dbm-services/common/go-pubpkg/errno"
	"fmt"
	"log/slog"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/asaskevich/govalidator"
	"golang.org/x/time/rate"
)

// ReplaceHostInMysqlGrants 替换mysql授权语句中的host
func ReplaceHostInMysqlGrants(userGrants []UserGrant, targetIp []string) []UserGrant {
	newUserGrants := NewUserGrants{}
	wg := sync.WaitGroup{}

	regForCreateUser := regexp.MustCompile(`(?i)^\s*CREATE USER `) // CREATE USER变为CREATE USER IF NOT EXISTS
	regForConnLog := regexp.MustCompile("`test`.`conn_log`")       // `test`.`conn_log`变为 infodba_schema.conn_log
	regHost := regexp.MustCompile("(?U)@['`].*['`]")               // 非贪婪模式
	for _, row := range userGrants {
		wg.Add(1)
		go func(row UserGrant) {
			defer wg.Done()
			var tmp []string
			var grantTmp string
			for _, grant := range row.Grants {
				if regForCreateUser.MatchString(grant) {
					grant = regForCreateUser.ReplaceAllString(grant, `CREATE USER /*!50706 IF NOT EXISTS */ `)
				}
				if regForConnLog.MatchString(grant) {
					grant = regForConnLog.ReplaceAllString(grant, `infodba_schema.conn_log`)
				}
				for _, ip := range targetIp {
					grantTmp = regHost.ReplaceAllString(grant, fmt.Sprintf("@'%s'", ip))
					tmp = append(tmp, grantTmp)
				}
			}
			row.Grants = tmp
			newUserGrants.mu.Lock()
			newUserGrants.Data = append(newUserGrants.Data, row)
			newUserGrants.mu.Unlock()
		}(row)
	}
	wg.Wait()
	return newUserGrants.Data
}

// ReplaceHostInProxyGrants 替换proxy新增白名单语句中的host
func ReplaceHostInProxyGrants(grants []string, targetIp []string) []string {
	var newGrants []string
	var grantTmp string
	re := regexp.MustCompile("(?U)@.*'")
	for _, item := range grants {
		for _, ip := range targetIp {
			grantTmp = re.ReplaceAllString(item, fmt.Sprintf("@%s'", ip))
			newGrants = append(newGrants, grantTmp)
		}
	}
	return newGrants
}

// GetProxyPrivilege 获取proxy白名单
func GetProxyPrivilege(address string, hosts []string, bkCloudId int64, specifiedUser string) ([]string, error) {
	var grants []string
	var reStr string
	sql := "select * from user;"
	monitorReg := regexp.MustCompile("MONITOR@.*")
	var queryRequest = QueryRequest{[]string{address}, []string{sql}, true, 30, bkCloudId}
	output, err := OneAddressExecuteProxySql(queryRequest)
	if err != nil {
		return nil, errno.ClonePrivilegesFail.Add(fmt.Sprintf(
			"execute (%s) in bk_cloud_id (%d) instance (%s) get an error:%s", sql, bkCloudId, address,
			err.Error()))
	}
	usersResult := output.CmdResults[0].TableData
	if len(hosts) == 0 {
		// 实例间克隆
		for _, user := range usersResult {
			//addUserSQL := fmt.Sprintf("refresh_users('%s','+')", user["user@ip"].(string))
			grants = append(grants, user["user@ip"].(string))
		}
	} else {
		// 客户端克隆
		for _, h := range hosts {
			reStr = fmt.Sprintf("%s|.*@%s$", reStr, strings.ReplaceAll(h, ".", "\\."))
			// 客户端克隆并且指定了user
			if specifiedUser != "" {
				reStr = fmt.Sprintf("%s|^%s@%s$", reStr, specifiedUser, strings.ReplaceAll(h, ".", "\\."))
			}
		}
		reStr = strings.TrimPrefix(reStr, "|")
		slog.Info("msg", "reStr", reStr)
		re := regexp.MustCompile(reStr)
		for _, user := range usersResult {
			tmpUser := user["user@ip"].(string)
			if re.MatchString(tmpUser) && !monitorReg.MatchString(tmpUser) {
				//addUserSQL := fmt.Sprintf("refresh_users('%s','+')", tmpUser)
				//grants = append(grants, addUserSQL)
				grants = append(grants, tmpUser)
			}
		}
	}
	return grants, nil
}

// ImportProxyPrivileges 导入proxy白名单
func ImportProxyPrivileges(grants []string, address string, bkCloudId int64) error {
	var errMsg Err
	wg := sync.WaitGroup{}
	limit := rate.Every(time.Millisecond * 20) // QPS：50
	burst := 50                                // 桶容量 50
	limiter := rate.NewLimiter(limit, burst)
	for _, item := range grants {
		errLimiter := limiter.Wait(context.Background())
		if errLimiter != nil {
			slog.Error("msg", "limiter.Wait", errLimiter)
			return errLimiter
		}
		wg.Add(1)
		go func(item string) {
			defer func() {
				wg.Done()
			}()
			queryRequest := QueryRequest{[]string{address}, []string{item}, true, 30, bkCloudId}
			_, err := OneAddressExecuteProxySql(queryRequest)
			if err != nil {
				AddError(&errMsg, address, err)
				return
			}
		}(item)
	}
	wg.Wait()
	if len(errMsg.errs) > 0 {
		return errno.ClonePrivilegesFail.Add(strings.Join(errMsg.errs, "\n"))
	}
	return nil
}

func validateIP(sourceIp string, targetIp []string, bkCloudId *int64) []string {
	var errMsg []string
	sourceIp = strings.TrimSpace(sourceIp)

	if bkCloudId == nil {
		errMsg = append(errMsg, errno.CloudIdRequired.Error())
	}

	// 检查是否是合法的实例
	result := govalidator.IsIP(sourceIp)
	if !result {
		errMsg = append(errMsg, fmt.Sprintf("Source ip (%s) is not a valid ip", sourceIp))
	}

	for _, ip := range targetIp {
		ip = strings.TrimSpace(ip)
		result = govalidator.IsIP(ip)
		if !result {
			errMsg = append(errMsg, fmt.Sprintf("Target ip (%s) is not a valid ip", targetIp))
		}
		if sourceIp == ip {
			errMsg = append(errMsg, "Source ip and target ip are the same one")
		}
	}

	if len(errMsg) > 0 {
		return errMsg
	}
	return nil
}

// AddError 添加错误信息，包括实例信息
func AddError(errMsg *Err, address string, err error) {
	errMsg.mu.Lock()
	errMsg.errs = append(errMsg.errs, address, err.Error())
	errMsg.mu.Unlock()
}

// AddErrorOnly 添加错误信息
func AddErrorOnly(errMsg *Err, err error) {
	errMsg.mu.Lock()
	errMsg.errs = append(errMsg.errs, err.Error())
	errMsg.mu.Unlock()
}

// AddResource 并行时构建数组
func AddResource(resources *Resource, resource OneCluster) {
	resources.mu.Lock()
	resources.resources = append(resources.resources, resource)
	resources.mu.Unlock()
}

// AddString 添加数组
func AddString(s *StringList, newString []string) {
	s.mu.Lock()
	s.l = append(s.l, newString...)
	s.mu.Unlock()
}
