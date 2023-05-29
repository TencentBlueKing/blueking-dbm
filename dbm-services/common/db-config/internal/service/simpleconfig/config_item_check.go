package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
	"fmt"
	"strings"

	"github.com/pkg/errors"
)

// AddConfigsRefToDiff TODO
func AddConfigsRefToDiff(configsRef map[string]*ConfigModelRef) []*model.ConfigModelOp {
	configsDiff := make([]*model.ConfigModelOp, 0)
	for _, configsMap := range configsRef {
		for optype, configs := range *configsMap {
			for _, c := range configs {
				configDiff := &model.ConfigModelOp{
					Config: c,
					OPType: optype,
				}
				configsDiff = append(configsDiff, configDiff)
			}
		}
	}
	return configsDiff
}

// BatchPreCheckPlat TODO
// 批量检查要写入的 conf_item 的上下层级合法性
// 返回一个map， key是conf_name, value 是需要处理的下级配置
func BatchPreCheckPlat(r *api.UpsertConfFilePlatReq, configs []*model.ConfigModel) (map[string]*ConfigModelRef, error) {
	var errs []error
	var configsRefMap = map[string]*ConfigModelRef{}
	for _, cn := range r.ConfNames {
		configsRef, err := PreCheckPlat(&r.ConfFileInfo.BaseConfFileDef, cn)
		if err != nil {
			errs = append(errs, err)
		} else {
			if len(*configsRef) > 0 {
				configsRefMap[cn.ConfName] = configsRef
			}
		}
	}
	// 存在不满足插入条件的 config item 集合
	if len(errs) > 0 {
		return configsRefMap, util.SliceErrorsToError(errs)
	}
	logger.Info("BatchPreCheckPlat precheck result: %+v", configsRefMap)
	return configsRefMap, nil
}

// BatchPreCheck TODO
func BatchPreCheck(configs []*model.ConfigModelView) (map[string]*ConfigModelRef, error) {
	var errs []error
	var configsRefMap = map[string]*ConfigModelRef{}
	for _, cn := range configs {
		configsRef, err := PreCheck(cn, false)
		if err != nil {
			errs = append(errs, err)
		} else {
			if len(*configsRef) > 0 {
				configsRefMap[cn.ConfName] = configsRef
			}
		}
	}
	// 存在不满足插入条件的 config item 集合
	if len(errs) > 0 {
		return configsRefMap, util.SliceErrorsToError(errs)
	}
	return configsRefMap, nil
}

// PreCheck TODO
func PreCheck(c *model.ConfigModelView, checkValue bool) (*ConfigModelRef, error) {
	if err := CheckConfNameAndValue(&c.ConfigModel, checkValue, "", "", ""); err != nil {
		return nil, err
	}
	return PrecheckConfigItemUpsert(c)
}

// PreCheckPlat TODO
func PreCheckPlat(f *api.BaseConfFileDef, cn *api.UpsertConfNames) (*ConfigModelRef, error) {
	c := &model.ConfigModel{
		Namespace: f.Namespace,
		ConfFile:  f.ConfFile,
		ConfType:  f.ConfType,
		ConfName:  cn.ConfName,
		ConfValue: cn.ValueDefault,
		BKBizID:   constvar.BKBizIDForPlat,
	}
	// 如果校验的 value_type 为空，任务前端没有传递 value_type, value_allowed 值，直接从后端取再校验
	if cn.ValueType == "" {
		if err := CheckConfNameAndValue(c, true, "", "", ""); err != nil {
			return nil, err
		}
	} else {
		if err := CheckConfNameAndValue(c, true, cn.ValueType, cn.ValueTypeSub, cn.ValueAllowed); err != nil {
			return nil, err
		}
	}
	cmv := &model.ConfigModelView{
		ConfigModel: *c,
		// no UpLevelInfo
	}
	return PrecheckConfigItemUpsert(cmv)
}

// PrecheckConfigItemUpsert TODO
// 检查当前配置项是否可以写入，add, update
func PrecheckConfigItemUpsert(c *model.ConfigModelView) (*ConfigModelRef, error) {

	up, down, err := c.GetConfigItemsAssociateNodes()
	if err != nil {
		return nil, err
	}
	upConfigs, err := c.GetConfigItemsAssociate(c.BKBizID, up)
	if err != nil {
		return nil, err
	}
	downConfig := make([]*model.ConfigModel, 0)
	if c.FlagLocked == 1 {
		downConfig, err = c.GetConfigItemsAssociate(c.BKBizID, down)
		if err != nil {
			return nil, err
		}
	}

	configsRef, err := CheckConfigItemWritable(&c.ConfigModel, upConfigs, downConfig)
	return configsRef, err
}

// ConfigModelRef2 TODO
// 存放与即将写入的 conf_item 有关的上下层级的节点操作信息
// "remove_ref":[{},{}] 需要删除的下级节点
// "notify":[{},{}] 配置值有变动的下级节点
type ConfigModelRef2 struct {
	OPConfig map[string][]*model.ConfigModel
}

// ConfigModelRef TODO
type ConfigModelRef map[string][]*model.ConfigModel

// Add TODO
func (d ConfigModelRef) Add(optype string, c *model.ConfigModel) {
	if _, ok := d[optype]; ok {
		d[optype] = append(d[optype], c)
	} else {
		d[optype] = []*model.ConfigModel{c}
	}
}

// CheckConfigItemWritable TODO
// 检查该配置项是否允许 写入/修改
// 输入的是统一配置项的 上下级配置
func CheckConfigItemWritable(current *model.ConfigModel, up, down []*model.ConfigModel) (*ConfigModelRef, error) {
	logger.Info("CheckConfigItemWritable current:%+v up:%+v down:%+v", current, up, down)
	// 检查上层级
	var errsString []string
	for _, c := range up {
		if c.FlagLocked == 1 {
			errsString = append(errsString, fmt.Sprintf("上层级 [%s] 已锁定配置项 [%s]", c.LevelName, c.ConfName))
		}
	}
	// 上级配置有加锁，不允许当前层级或者下级 存在显示配置项
	if len(errsString) > 0 {
		errStr := strings.Join(errsString, "\n")
		return nil, errors.New(errStr)
	}
	opConfigs := &ConfigModelRef{}

	// 检查下层级
	if current.FlagLocked == 1 {
		for _, c := range down {
			// delete 需要计划删除下级节点
			// notify 下级配置值与当前不一致
			// locked 下级有锁
			c.FlagDisable = -1
			opConfigs.Add(constvar.OPTypeRemoveRef, c)
			if c.FlagLocked == 0 && c.ConfValue != current.ConfValue {
				opConfigs.Add(constvar.OPTypeNotified, c)
			} else if c.FlagLocked == 1 && c.ConfValue != current.ConfValue {
				// 下级配置有锁，且与当前层级要加锁的配置值不相等，也强制下级产生红点
				opConfigs.Add(constvar.OPTypeLocked, c)
				opConfigs.Add(constvar.OPTypeNotified, c)
			} else if c.FlagLocked == 1 && c.ConfValue == current.ConfValue {
				// 下级配置有锁，且与当前层级要锁的配置值相同，可直接删除
				opConfigs.Add(constvar.OPTypeLocked, c)
			} else {
				// ignore or unreachable
			}
		}
		logger.Info("CheckConfigItemWritable down:%+v", opConfigs)
		return opConfigs, nil
	} else { // 当前配置不加锁
		return opConfigs, nil
	}
}
