package service

import (
	"fmt"
	"regexp"
	"strings"
	"sync"

	"dbm-services/common/go-pubpkg/errno"

	"github.com/asaskevich/govalidator"
)

// ReplaceHostInMysqlGrants 替换mysql授权语句中的host
func ReplaceHostInMysqlGrants(userGrants []UserGrant, sourceIp string, targetIp []string) []UserGrant {
	newUserGrants := NewUserGrants{}
	wg := sync.WaitGroup{}

	regForCreateUser := regexp.MustCompile(`(?i)^\s*CREATE USER `) // CREATE USER变为CREATE USER IF NOT EXISTS

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
				for _, ip := range targetIp {
					grantTmp = strings.ReplaceAll(grant, sourceIp, ip)
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
func ReplaceHostInProxyGrants(grants []string, sourceIp string, targetIp []string) []string {
	var newGrants []string
	var grantTmp string
	for _, item := range grants {
		for _, ip := range targetIp {
			grantTmp = strings.ReplaceAll(item, sourceIp, ip)
			newGrants = append(newGrants, grantTmp)
		}
	}
	return newGrants
}

// GetProxyPrivilege 获取proxy白名单
func GetProxyPrivilege(address string, host string, bkCloudId int64) ([]string, error) {
	var grants []string
	sql := "select * from user;"
	var queryRequest = QueryRequest{[]string{address}, []string{sql}, true, 30, bkCloudId}
	output, err := OneAddressExecuteProxySql(queryRequest)
	if err != nil {
		return nil, errno.ClonePrivilegesFail.Add(fmt.Sprintf(
			"execute (%s) in bk_cloud_id (%d) instance (%s) get an error:%s", sql, bkCloudId, address,
			err.Error()))
	}
	usersResult := output.CmdResults[0].TableData
	if host == "" {
		for _, user := range usersResult {
			addUserSQL := fmt.Sprintf("refresh_users('%s','+')", user["user@ip"].(string))
			grants = append(grants, addUserSQL)
		}
	} else {
		regexp := regexp.MustCompile(fmt.Sprintf(".*@%s$", strings.ReplaceAll(host, ".", "\\.")))
		for _, user := range usersResult {
			tmpUser := user["user@ip"].(string)
			if regexp.MatchString(tmpUser) {
				addUserSQL := fmt.Sprintf("refresh_users('%s','+')", tmpUser)
				grants = append(grants, addUserSQL)
			}
		}

	}
	return grants, nil
}

// ImportProxyPrivileges 导入proxy白名单
func ImportProxyPrivileges(grants []string, address string, bkCloudId int64) error {
	var errMsg Err
	wg := sync.WaitGroup{}
	tokenBucket := make(chan int, 10)

	for _, item := range grants {
		wg.Add(1)
		tokenBucket <- 0
		go func(item string) {
			defer func() {
				<-tokenBucket
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
	close(tokenBucket)
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
