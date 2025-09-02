// Package mysql_proxy TODO
/*
 * @Description: 克隆proxy的user权限
 */
package mysql_proxy

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"errors"
	"strconv"
	"strings"
	"sync"
)

// CloneProxyUserComp TODO
type CloneProxyUserComp struct {
	GeneralParam *components.GeneralParam
	Params       *CloneProxyUserParam
}

// CloneProxyUserParam TODO
// payload param
type CloneProxyUserParam struct {
	SourceAddress string   `json:"source_address"`
	DestAddresses []string `json:"dest_addresses"`
}

func (p *CloneProxyUserComp) CloneProxyUser() (err error) {
	var mut sync.Mutex
	var wg sync.WaitGroup
	wg.Add(len(p.Params.DestAddresses))
	logger.Info("set wg group to %d", len(p.Params.DestAddresses))

	for _, destAddress := range p.Params.DestAddresses {
		logger.Info("go to clone to %s", destAddress)
		go func(destAddress string) {
			defer wg.Done()
			e := p.cloneOneProxyUser(destAddress)
			if e != nil {
				mut.Lock()
				err = errors.Join(err, e)
				mut.Unlock()
			}
		}(destAddress)
	}
	wg.Wait()

	return
}

// CloneProxyUser 在源proxy克隆user白名单给目标proxy
func (p *CloneProxyUserComp) cloneOneProxyUser(destAddress string) (err error) {
	sourceWorker, err := p.connProxyAdmin(p.Params.SourceAddress)
	if err != nil {
		return err
	}
	defer sourceWorker.Close()
	logger.Info("connect %s success", p.Params.SourceAddress)

	destWorker, err := p.connProxyAdmin(destAddress)
	if err != nil {
		return err
	}
	defer destWorker.Close()
	logger.Info("connect %s success", destAddress)

	err = sourceWorker.CloneProxyUser(destWorker)
	if err != nil {
		logger.Error(
			"clone proxy user from %s to %s failed,%s", p.Params.SourceAddress, destAddress, err.Error(),
		)
		return err
	}
	logger.Info("clone proxy user from %s to %s success", p.Params.SourceAddress, destAddress)
	return
}

func (p *CloneProxyUserComp) connProxyAdmin(address string) (worker *native.ProxyAdminDbWork, err error) {
	splitAddress := strings.Split(address, ":")
	ip := splitAddress[0]
	port, err := strconv.Atoi(splitAddress[1])
	if err != nil {
		return nil, err
	}
	worker, err = native.InsObject{
		Host: ip,
		Port: port,
		User: p.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
		Pwd:  p.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
	}.ConnProxyAdmin()
	if err != nil {
		return nil, err
	}
	return
}

// Example TODO
func (p *CloneProxyUserComp) Example() interface{} {
	comp := CloneProxyUserComp{
		Params: &CloneProxyUserParam{
			SourceAddress: "127.0.0.1:3306",
			DestAddresses: []string{"127.0.0.2:3306"},
		},
	}
	return comp
}
